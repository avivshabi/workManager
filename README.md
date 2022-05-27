# Queue & Work Management for Parallel Processing  
A simple Queue & Work Management system using AWS EC2 instances only.  
The Queue consists of 2 fully seperated nodes that sync the data between them (redundancy).  
In addition to the Server Application, each node runs a scheduled script to creates worker nodes as needed.

## Run Locally 

Please make sure you have installed and configured AWS CLI on your local machine.  
Note: You should have access to a RedisCluster (Local or Remote)  

```
git clone git@github.com:avivshabi/workManager.git app  
cd app
pip3 install -r requirements.txt --upgrade
uvicorn main:app --host 0.0.0.0 --port 5000
```

## Deploy to AWS

Please make sure you have installed and configured AWS CLI on your local machine.  

```
git clone git@github.com:avivshabi/workManager.git app  
cd app
./setup.sh
```

## API
### PUT /enqueue  

Add a new job to the queue
```
method: PUT
path: /enqueue?iterations=<NUM OF ITERATIONS TO PERFORM>
body: {
            'data': <BINARY DATA>    
      }
response type: json
response: { 
             'Work ID': <GENERATED WORK ID>
          }
```

### POST /pullCompleted  

Get a list of completed jobs
```
method: POST
path: /pullCompleted?top=<NO. OF INSTANCES TO RETURN>
body: None
response type: json
response: [
             {
                'Work ID': <GENERATED WORK ID>,
                'Value': <CALCULATED VALUE>
                
             },
             ...
          ]
```

## Failure Modes Handling

### Overload -

Both main nodes could benefit from a load balancer that will help to uniformly distribute all received requests  
between available servers.  
The load balancer will receive all requests and distribute them among the available endpoints servers (that will be  
dynamically created and deleted, based on system load & needs).  
In addition to a load balancer, a full separation between the web server to the database nodes (Redis Cluster),
as well as, utilization of additional servers for Redis Master nodes and Replicas will enable to dramatically lower the  
load on each node. Furthermore, utilization of Replica nodes would also enable to lower the load on master nodes.  
Lastly, Worker nodes creation & termination policy need to be dynamically adjusted in order to respect SLA and
provide a more robust solution.

### Security breaches -

The current implementation has lots of security flaws that a production level system must not have.  
A production level system should maintain a stricter security policy when it comes to access system components  
other than the public webserver.  
Thus, we should enforce encrypted connections policy using TLS, enable password protection and TLS 
over all Redis Cluster nodes and to maintain a more well-defined & strict security group policy in our AWS EC2   
instances (that is, allow only known & live system components to connect with other system components  
through specific ports).

### HW & SW failures -

#### Hardware failure -

Hardware failure such as Network failures and other hardware components often occur due to lots of diverse  
reasons (earthquakes, terror attack, electricity shortage, etc.).  
In order to protect our system from such failures, we should have a redundancy in every component we use.  
Additionally, we should have backups and replication of our system in multiple availability zones.  

#### Software failure -

Application level failures may occur and should be handled wisely. 
First, a production level system should not trust user input and thus, should parse & check every input received 
before execution of any risky operation (save to DB, calculations, etc.).  
In addition, the app should handle exception and make sure that a single failure won't disable the entire system.

The system should be monitored on a regular basis in order to find & repair such failures.

### Slow response times (Performance) -

Slow response times might be the result of a security breach or that the system got overloaded due to poor  
configurations and policy. But, it can also be the result of locality issues.  
First, if a system serve users across the world, we should consider having replication of the entire infrastructure  
in several regions.  
Moreover, the system shouldn't be too sparse - that is, broken into too many unnecessary remote components.  
Lastly, the system should enable a caching mechanism.


