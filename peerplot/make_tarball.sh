#!/bin/sh

VERSION="0.0.7"
FILE="peerplot-$VERSION"

mkdir -p $FILE
mkdir -p "$FILE/peerplot"
mkdir -p "$FILE/examples"

cp -f ../README.txt $FILE
sed "s/%VERSION%/${VERSION}/g" <setup.py >$FILE/setup.py
cp -f examples/plot.py $FILE/examples
sed "s/%VERSION%/${VERSION}/g" <peerplot/__init__.py >$FILE/peerplot/__init__.py
cp -f peerplot/websocket.py $FILE/peerplot
cp -f peerplot/h5frame.py $FILE/peerplot
cp -f peerplot/backend_h5canvas.py $FILE/peerplot
cp -f peerplot/rendererh5canvas.py $FILE/peerplot

tar -cf "$FILE.tar" $FILE
gzip "$FILE.tar"

if [ ! -d server/downloads ]; then
    mkdir -p "server/downloads"
fi
mv "$FILE.tar.gz" server/downloads

rm -rf $FILE
mkdir -p $FILE

cp -fR server/* $FILE
sed "s/%FILE%/${FILE}.tar.gz/g" <$FILE/templates/index.html >$FILE/templates/index.html.1
mv $FILE/templates/index.html.1 $FILE/templates/index.html
tar -cf "$FILE.tar" $FILE
gzip "$FILE.tar"
rm -rf $FILE

