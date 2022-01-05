# sa-hunter 
Maps Kubernetes serviceaccounts, pods and nodes to their assigned roles and clusterroles, i.e. their permissions.

## Help

```
usage: sa_hunter.py [-h] [-a] [-o OUT_FILE] [-l]

Correlates serviceaccounts, pods and nodes to the roles and clusterroles that grant them permissions.

optional arguments:
  -h, --help   Show this help message and exit
  -a           Show all service accounts, not only those assigned to a pod
  -o OUT_FILE  Save results to output file
  -l           Load mode, print results regardless of -o
```

## Schema
```json
[
    {
        "name": "serviceaccount name",
        "namespace": "serviceaccount namespace",
        "nodes": [
            {
                "name": "the node hosting the following pods",
                "pods": [
                    "a pod assigned the service account"
                    "a pod assigned the service account"
                ]
            },
            {
                "name": "the node hosting the following pods",
                "pods": [
                    "a pod assigned the service account"
                ]
            }
        ],
        "providerIAM": 
            {
                "aws": "AWS role granted to this serviceaccount via the 'eks.amazonaws.com/role-arn' annotation, if exists"
                "gke": "GCP service account binded to this serviceaccount via the 'iam.gke.io/gcp-service-account' annotation, if exists"
            },    
        "roles": [
            {
                "name": "role or clusterrole binded to the serviceaccount",
                "namespace": "namespace where permissions are in effect, excluded for clusterroles granted via clusterrolebindings"
                "rules": []
            }
        ]
    },
    ...
]
```
