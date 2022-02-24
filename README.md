# sa-hunter 
Correlates serviceaccounts and pods to the permissions granted to them via rolebindings and clusterrolesbindings.

For clusters hosted on managed Kubernetes services, `sa-hunter` identifies serviceaccount annotations that assign cloud provider IAM entities to Kubernetes serviceaccounts. Currently `sa-hunter` supports serviceaccount annotations on EKS and GKE.


## Quick Start
`python3` and `pip3` are required.
1. Clone this repository.
```bash
git clone https://github.com/twistlock/sa-hunter
```
2. Install  the required python packages using pip.
```bash
pip3 install -r sa-hunter/requirements.txt
```
3. Connect `kubectl` to your cluster.
4. Run `sa-hunter`.
```bash
./sa-hunter/sa_hunter.py
```

## Help

```
usage: sa_hunter.py [-h] [-a] [-o OUT_FILE] [-l]

Correlates serviceaccounts and pods to the permissions granted to them via rolebindings and clusterrolesbindings.

optional arguments:
  -h, --help   show this help message and exit
  -a           show all service accounts, not only those assigned to a pod
  -o OUT_FILE  save results to output file
  -l           loud mode, print results regardless of -o
```

## Schema
```json
{
    "metadata": {
        "cluster": "cluster name from the current kubectl context",
        "platform": "eks, gke or empty",
        "version": "cluster Kubernetes version"
    },
    "serviceaccounts": [
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
            "providerIAM": // omitempty
                {
                    "aws": "AWS role granted to this serviceaccount via the 'eks.amazonaws.com/role-arn' annotation, if exists",
                    "gcp": "GCP service account binded to this serviceaccount via the 'iam.gke.io/gcp-service-account' annotation, if exists"
                },    
            "roles": [
                {
                    "name": "role or clusterrole binded to the serviceaccount",
                    "namespace": "namespace where permissions are in effect, excluded for clusterroles granted via clusterrolebindings", // omitempty
                    "rules": [] // k8s rule format
                }
            ]
        },
    ],
    "nodes": [
        {
            "name": "node name",
            "serviceaccounts": [
                "list of SAs hosted on this node",
                "format is namespace:name",
            ]
        },
        {
            "name": "node name",
            "serviceaccounts": [
                "namespace:name"
            ]
        },
    ]
}
```
