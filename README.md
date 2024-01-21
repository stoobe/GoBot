# GoBot


## AWS EC2 Setup
* Amazon Linux
* t2.micro
* add EBS, 8GB, /dev/sdb (second HD)

* Setup:
sudo yum update
curl -O https://bootstrap.pypa.io/get-pip.py
python3 get-pip.py --user
echo "export PATH=~/.local/bin:\$PATH" >> .bashrc
source .bashrc
pip install discord attrs
pip install --upgrade discord attrs
sudo yum install git
git clone https://github.com/stoobe/GoBot.git
sudo yum install emacs-nox