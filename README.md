# GoBot

pipreqs .

pip install -r requirements.txt


## AWS EC2 Setup
* Amazon Linux
* t2.micro
* add EBS, 8GB, /dev/sdb (second HD)

* Setup:
sudo yum update
sudo yum install git emacs-nox 

sudo timedatectl set-timezone America/New_York

curl -O https://bootstrap.pypa.io/get-pip.py
python3 get-pip.py --user
echo "export PATH=~/.local/bin:\$PATH" >> .bashrc
source .bashrc
rm get-pip.py

git clone https://github.com/stoobe/GoBot.git

cd ~/GoBot
pip install -r requirements.txt





pip install SQLAlchemy
sudo yum install mariadb
sudo yum install wget
wget https://r.mariadb.com/downloads/mariadb_repo_setup
echo "30d2a05509d1c129dd7dd8430507e6a7729a4854ea10c9dcf6be88964f3fdc25  mariadb_repo_setup"     | sha256sum -c -
chmod +x mariadb_repo_setup
sudo ./mariadb_repo_setup    --mariadb-server-version="mariadb-10.6"
sudo yum install MariaDB-shared MariaDB-devel
pip3 install mariadb
which gcc
sudo yum provides '*bin/gcc'
sudo yum group install "Development Tools"
which gcc
pip3 install mariadb
pip install mysqlclient











 ls
    2  sudo yum update
    3  sudo yum install python3-devel mysql-devel pkgconfig
    4  sudo yum install python3-devel mysql-dev pkgconfig
    5  sudo yum install python3-devel pkgconfig
    6  sudo yum install mysql-devel
    7  yum --help
    8  yum --help list
    9  yum --help find
   10  sudo yum install mysql-community-server
   11  sudo emacs /etc/yum/pluginconf.d/subscription-manager.conf
   12  sudo nano /etc/yum/pluginconf.d/subscription-manager.conf
   13  sudo yum install git emacs-nox
   14  sudo emacs /etc/yum/pluginconf.d/subscription-manager.conf
   15  sudo yum install mysql-community-server
   16  yum clean all
   17  sudo yum clean all
   18  sudo yum install mysql-community-server
   19  ls
   20  pwd
   21  sudo timedatectl set-timezone America/New_York
   22  curl -O https://bootstrap.pypa.io/get-pip.py
   23  python3 get-pip.py --user
   24  echo "export PATH=~/.local/bin:\$PATH" >> .bashrc
   25  source .bashrc
   26  rm get-pip.py
   27  ls
   28  ll
   29  ls -a
   30  pip install SQLAlchemy mysqlclient
   31  pip install SQLAlchemy
   32  pip install mysqlclient
   33  pip install mariadb
   34  sudo yum mariadb105
   35  sudo yum mariadb
   36  sudo yum install mariadb
   37  pip install mysqlclient
   38  pip install mariadb
   39  sudo yum install MariaDB-shared MariaDB-devel
   40  sudo yum install wget
   41  wget https://r.mariadb.com/downloads/mariadb_repo_setup
   42  ls
   43  echo "30d2a05509d1c129dd7dd8430507e6a7729a4854ea10c9dcf6be88964f3fdc25  mariadb_repo_setup"     | sha256sum -c -
   44  chmod +x mariadb_repo_setup
   45  ll
   46  sudo ./mariadb_repo_setup    --mariadb-server-version="mariadb-10.6"
   47  sudo yum install MariaDB-shared MariaDB-devel
   48  pip3 install mariadb
   49  which gcc
   50  su -
   51  wu
   52  su
   53  sudo subscription-manager repos --list | egrep devtools
   54  sudo yum provides '*bin/gcc'
   55  sudo yum group install "Development Tools"
   56  which gcc
   57  pip3 install mariadb
   58  history > hist.txt
   59  wc hist.txt
   60  pip install mysqlclient
   61  history | wc
   62  history > hist.txt