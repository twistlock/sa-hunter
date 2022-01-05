# sa-hunter 
Maps Kubernetes serviceaccounts, pods and nodes to their assigned roles and clusterroles, i.e. their permissions.

## Help

```
usage: sa_hunter.py [-h] [-a] [-o OUT_FILE] [-l]

Correlates serviceaccounts, pods and nodes to the roles and clusterroles that grant them permissions.

optional arguments:
  -h, --help   show this help message and exit
  -a           Show all service accounts, not only those assigned to a pod
  -o OUT_FILE  Save results to output file
  -l           Load mode, print results regardless of -o
```
