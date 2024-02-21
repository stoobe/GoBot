# GoBot

pipreqs .

pip install -r requirements.txt


## AWS EC2 Setup
* Amazon Linux
* t2.micro
* add EBS, 8GB, /dev/sdb (second HD)

* Setup:
sudo yum update
sudo yum install mariadb105 git emacs-nox python-devel

sudo dnf update
sudo dnf install mariadb105 git emacs-nox python-devel

curl -O https://bootstrap.pypa.io/get-pip.py
python3 get-pip.py --user
echo "export PATH=~/.local/bin:\$PATH" >> .bashrc
source .bashrc
rm get-pip.py

git clone https://github.com/stoobe/GoBot.git

pip install pipupgrade
pipupgrade --verbose --latest --yes


pip install -r requirements.txt

pip install discord attrs
pip install --upgrade discord attrs

