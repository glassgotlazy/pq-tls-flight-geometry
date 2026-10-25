set -e
V=3.5.4; U=https://github.com/openssl/openssl/releases/download/openssl-$V
mkdir -p ~/build && cd ~/build
curl -fsSL -o openssl-$V.tar.gz $U/openssl-$V.tar.gz
curl -fsSL -o openssl-$V.tar.gz.sha256 $U/openssl-$V.tar.gz.sha256
EXP=$(awk '{print $1}' openssl-$V.tar.gz.sha256); GOT=$(sha256sum openssl-$V.tar.gz | awk '{print $1}')
echo "sha256 expected=$EXP got=$GOT"; [ "$EXP" = "$GOT" ] || { echo "SHA-256 MISMATCH"; exit 1; }
rm -rf openssl-$V && tar xzf openssl-$V.tar.gz && cd openssl-$V
./Configure --prefix=/opt/ossl35 --libdir=lib no-tests no-docs > ../configure.log 2>&1
make -j2 > ../make.log 2>&1
sudo make install_sw > ../install.log 2>&1
LD_LIBRARY_PATH=/opt/ossl35/lib /opt/ossl35/bin/openssl version
