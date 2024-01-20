# GoBot


## AWS EC2 Setup
* Amazon Linux
* t2.micro
* add EBS, 15GB, /dev/sdb (second HD)

* Setup:
sudo yum update
curl -O https://bootstrap.pypa.io/get-pip.py
sudo python3 get-pip.py
sudo pip install discord wheel recordclass
git clone https://github.com/stoobe/GoBot.git