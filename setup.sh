#!/bin/sh
# debug
# set -o xtrace

ID=$(gdate +'%N')
KEY_NAME="cloud-course-$ID"
KEY_PEM="$KEY_NAME.pem"
AWS_SETTINGS_FILE=".env"

echo "AWS_ACCESS_KEY_ID=`aws configure get aws_access_key_id`" > $AWS_SETTINGS_FILE
echo "AWS_SECRET_ACCESS_KEY=`aws configure get aws_secret_access_key`" >> $AWS_SETTINGS_FILE
echo "AWS_DEFAULT_REGION=`aws configure get region`" >> $AWS_SETTINGS_FILE

echo "Create key pair $KEY_PEM to connect to instances and save locally"
aws ec2 create-key-pair --key-name $KEY_NAME \
    | jq -r ".KeyMaterial" > $KEY_PEM

# secure the key pair
chmod 400 $KEY_PEM

SEC_GRP="my-sg-$ID"

echo "Setup firewall $SEC_GRP"
aws ec2 create-security-group   \
    --group-name $SEC_GRP       \
    --description "Access my instances"

# figure out my ip
MY_IP=$(curl ipinfo.io/ip)
echo "My IP: $MY_IP"

echo "Setup rule allowing TCP (port 5000) access to everyone"
aws ec2 authorize-security-group-ingress        \
    --group-name $SEC_GRP --port 5000 --protocol tcp \
    --cidr 0.0.0.0/0 >/dev/null

echo "Setup rule allowing TCP (ports 6379 - 6381) access to everyone"
aws ec2 authorize-security-group-ingress        \
    --group-name $SEC_GRP --port 6379-6381 --protocol tcp \
    --cidr 0.0.0.0/0 >/dev/null

echo "Setup rule allowing TCP (ports 16379 - 16381) access to everyone"
aws ec2 authorize-security-group-ingress        \
    --group-name $SEC_GRP --port 16379-16381 --protocol tcp \
    --cidr 0.0.0.0/0 >/dev/null

echo "Setup rule allowing SSH access to $MY_IP only"
aws ec2 authorize-security-group-ingress        \
    --group-name $SEC_GRP --port 22 --protocol tcp \
    --cidr $MY_IP/32 >/dev/null

UBUNTU_AMI="ami-09d56f8956ab235b3"

echo "Creating Ubuntu instance (master 1)..."
RUN_INSTANCES=$(aws ec2 run-instances   \
    --image-id $UBUNTU_AMI        \
    --instance-type t2.micro            \
    --key-name $KEY_NAME                \
    --security-groups $SEC_GRP)

INSTANCE_ID=$(echo $RUN_INSTANCES | jq -r '.Instances[0].InstanceId')

echo "Waiting for instance creation..."
aws ec2 wait instance-running --instance-ids $INSTANCE_ID

IP_MASTER1=$(aws ec2 describe-instances  --instance-ids $INSTANCE_ID |
    jq -r '.Reservations[0].Instances[0].PublicIpAddress'
)

echo "New instance $INSTANCE_ID @ $IP_MASTER1 created"

echo "Creating Ubuntu instance (master 2)..."
RUN_INSTANCES=$(aws ec2 run-instances   \
    --image-id $UBUNTU_AMI        \
    --instance-type t2.micro            \
    --key-name $KEY_NAME                \
    --security-groups $SEC_GRP)

INSTANCE_ID=$(echo $RUN_INSTANCES | jq -r '.Instances[0].InstanceId')

echo "Waiting for instance creation..."
aws ec2 wait instance-running --instance-ids $INSTANCE_ID

IP_MASTER2=$(aws ec2 describe-instances  --instance-ids $INSTANCE_ID |
    jq -r '.Reservations[0].Instances[0].PublicIpAddress'
)

echo "New instance $INSTANCE_ID @ $IP_MASTER2 created"

sleep 30

echo "Deploying code to production"
scp -v -i $KEY_PEM -o "StrictHostKeyChecking=no" -o "ConnectionAttempts=60" $AWS_SETTINGS_FILE launch.sh ubuntu@$IP_MASTER1:/home/ubuntu/
scp -v -i $KEY_PEM -o "StrictHostKeyChecking=no" -o "ConnectionAttempts=60" $AWS_SETTINGS_FILE launch.sh ubuntu@$IP_MASTER2:/home/ubuntu/

echo "Setup production environment on both instances"
ssh -tt -i $KEY_PEM -o "StrictHostKeyChecking=no" -o "ConnectionAttempts=10" ubuntu@$IP_MASTER1 'sh ./launch.sh' < /dev/tty
ssh -tt -i $KEY_PEM -o "StrictHostKeyChecking=no" -o "ConnectionAttempts=10" ubuntu@$IP_MASTER2 'sh ./launch.sh' < /dev/tty

ssh -i $KEY_PEM -o "StrictHostKeyChecking=no" -o "ConnectionAttempts=10" ubuntu@$IP_MASTER2 <<EOF
    echo "Preparing Redis masters..."
    mkdir node4
    mkdir node5
    mkdir node6
    sudo docker run --privileged --net=host --name redis-node4 -d -e ALLOW_EMPTY_PASSWORD=yes -e REDIS_NODES="$IP_MASTER1 $IP_MASTER2" -v node4:/bitnami bitnami/redis-cluster:latest
    sudo docker run --privileged --net=host --name redis-node5 -d -e ALLOW_EMPTY_PASSWORD=yes -e REDIS_PORT_NUMBER=6380 -e REDIS_NODES="$IP_MASTER1 $IP_MASTER2" -v node5:/bitnami bitnami/redis-cluster:latest
    sudo docker run --privileged --net=host --name redis-node6 -d -e ALLOW_EMPTY_PASSWORD=yes -e REDIS_PORT_NUMBER=6381 -e REDIS_NODES="$IP_MASTER1 $IP_MASTER2" -v node6:/bitnami bitnami/redis-cluster:latest
    echo "Starting FastAPI server..."
    cp $AWS_SETTINGS_FILE app/.env
    cd app
    nohup uvicorn main:app --host 0.0.0.0 --port 5000 &>/dev/null &
    echo "Starting Load Balancer..."
    nohup python3 workers_manager.py &>/dev/null &
    exit
EOF

ssh -i $KEY_PEM -o "StrictHostKeyChecking=no" -o "ConnectionAttempts=10" ubuntu@$IP_MASTER1 <<EOF
    echo "Preparing Redis masters..."
    sudo mkdir node1
    sudo mkdir node2
    sudo mkdir node3
    sudo docker run --privileged --net=host --name redis-node1 -d -e ALLOW_EMPTY_PASSWORD=yes -e REDIS_NODES="$IP_MASTER1 $IP_MASTER2" -v node1:/bitnami bitnami/redis-cluster:latest
    sudo docker run --privileged --net=host --name redis-node2 -d -e ALLOW_EMPTY_PASSWORD=yes -e REDIS_PORT_NUMBER=6380 -e REDIS_NODES="$IP_MASTER1 $IP_MASTER2" -v node2:/bitnami bitnami/redis-cluster:latest
    sudo docker run --privileged --net=host --name redis-node3 -d -e ALLOW_EMPTY_PASSWORD=yes -e REDIS_PORT_NUMBER=6381 -e REDIS_NODES="$IP_MASTER1 $IP_MASTER2" -v node3:/bitnami bitnami/redis-cluster:latest
    echo "Create Redis cluster..."
    sleep 30
    redis-cli --cluster create $IP_MASTER2:6379 $IP_MASTER2:6380 $IP_MASTER2:6381 $IP_MASTER1:6379 $IP_MASTER1:6380 $IP_MASTER1:6381 --cluster-replicas 0 --cluster-yes
    echo "Starting FastAPI server..."
    cp $AWS_SETTINGS_FILE app/.env
    cd app
    nohup uvicorn main:app --host 0.0.0.0 --port 5000 &>/dev/null &
    echo "Starting Load Balancer..."
    nohup python3 workers_manager.py &>/dev/null &
    exit
EOF

sleep 20
echo "Test that it all worked (access status route)"
curl  --retry-connrefused --retry 10 --retry-delay 1  http://$IP_MASTER1:5000/status
echo "\nLog to master 1: http://$IP_MASTER1:5000/status"
curl  --retry-connrefused --retry 10 --retry-delay 1  http://$IP_MASTER2:5000/status
echo "\nLog to master 2: http://$IP_MASTER2:5000/status"