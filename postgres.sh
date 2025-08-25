#!/bin/bash

# 1) Kill whatever’s listening on 5433
lsof -ti tcp:5433 | xargs -r kill

# 2) Open SSH tunnel
ssh -f -i ~/.ssh/id_rsa \
    -L 5433:dev.cu32ckk2u1cc.us-east-1.rds.amazonaws.com:5432 \
    ubuntu@ec2-54-161-209-13.compute-1.amazonaws.com \
    -N

# 4) Tear the tunnel down
# pkill -f "ssh -i ~/.ssh/id_rsa -L 5433"
