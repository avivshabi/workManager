#!/bin/sh
echo "Starting setup..."
sudo apt -yf install
sudo apt -y update
sudo apt -y install git
sudo apt -y install python3-pip
sudo apt -y install uvicorn
sudo apt -y install docker.io
sudo apt -y install redis-tools
echo "Installing AWS CLI..."
pip3 install --upgrade awscli
sudo apt -y install awscli zip
git clone https://github.com/avivshabi/workManager.git app
echo "Successfully cloned github code..."
cd app
echo "Installing required packages..."
pip3 install -r requirements.txt --upgrade