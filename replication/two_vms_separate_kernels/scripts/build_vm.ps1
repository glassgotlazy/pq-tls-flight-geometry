# build_vm.ps1 - import the Ubuntu cloud OVA as a Workstation VM and configure it for the PH experiment.
# usage: build_vm.ps1 -Name pqa -MgmtMac 00:50:56:3a:77:01 -TestMac 00:50:56:3a:77:11 -TestIp 192.168.77.1
param([string]$Name,[string]$MgmtMac,[string]$TestMac,[string]$TestIp)
$ErrorActionPreference='Stop'
$vmw='C:\Program Files (x86)\VMware\VMware Workstation'
$root='<HOME>\VMs\pqtls'; $ova="$root\img\ubuntu-24.04-server-cloudimg-amd64.ova"
$dir="$root\$Name"; $vmx="$dir\$Name.vmx"
if (Test-Path $dir) { throw "$dir already exists" }
& "$vmw\OVFTool\ovftool.exe" --acceptAllEulas --allowExtraConfig --name=$Name $ova "$root" | Out-Host
if (-not (Test-Path $vmx)) { throw "import failed: $vmx missing" }
$pub=(Get-Content "$env:USERPROFILE\.ssh\id_ed25519_pqvm.pub" -Raw).Trim()
$meta=@"
instance-id: $Name-1
local-hostname: $Name
network:
  version: 2
  ethernets:
    mgmt0:
      match: {macaddress: "$MgmtMac"}
      set-name: mgmt0
      dhcp4: true
    test0:
      match: {macaddress: "$TestMac"}
      set-name: test0
      addresses: [$TestIp/24]
"@
$user=@"
#cloud-config
ssh_authorized_keys:
  - $pub
package_update: true
packages: [build-essential, ethtool, tcpdump, python3-numpy, perl, curl]
"@
$b64={ param($s) [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes(($s -replace "`r",''))) }
# drop keys we redefine, then append ours
$keep=Get-Content $vmx | Where-Object { $_ -notmatch '^(memsize|numvcpus|ethernet[01]\.|guestinfo\.)' }
$add=@(
 'memsize = "1536"','numvcpus = "2"',
 'ethernet0.present = "TRUE"','ethernet0.connectionType = "nat"','ethernet0.virtualDev = "vmxnet3"',
 'ethernet0.addressType = "static"',"ethernet0.address = `"$MgmtMac`"",
 'ethernet1.present = "TRUE"','ethernet1.connectionType = "pvn"','ethernet1.pvnID = "52 b1 7a 3c 77 00 00 01-a0 0b 5e 12 77 00 00 01"',
 'ethernet1.virtualDev = "vmxnet3"','ethernet1.addressType = "static"',"ethernet1.address = `"$TestMac`"",
 "guestinfo.metadata = `"$(& $b64 $meta)`"",'guestinfo.metadata.encoding = "base64"',
 "guestinfo.userdata = `"$(& $b64 $user)`"",'guestinfo.userdata.encoding = "base64"'
)
Set-Content -Path $vmx -Value ($keep + $add) -Encoding ascii
"configured $vmx"
