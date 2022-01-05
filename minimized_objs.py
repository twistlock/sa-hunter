class MinimizedServiceAccount():
    def __init__(self, sa_obj, nodes=[]):
        self.name = sa_obj["metadata"]["name"]
        self.namespace = sa_obj["metadata"]["namespace"]
        self.nodes = nodes
        self.roles = []
        self.add_provider_IAM(sa_obj)

    def add_provider_IAM(self, sa_obj):
        self.add_eks_iam_annotaions(sa_obj)
        self.add_gke_iam_annotaions(sa_obj)

    def add_eks_iam_annotaions(self, sa_obj):
        if "annotations" in sa_obj["metadata"]:
            if "eks.amazonaws.com/role-arn" in sa_obj["metadata"]["annotations"]:
                if not hasattr(self, 'providerIAM'):
                    self.providerIAM = {}
                self.providerIAM["aws"] = sa_obj["metadata"]["annotations"]["eks.amazonaws.com/role-arn"]

    def add_gke_iam_annotaions(self, sa_obj):
        if "annotations" in sa_obj["metadata"]:
            if "iam.gke.io/gcp-service-account" in sa_obj["metadata"]["annotations"]:
                if not hasattr(self, 'providerIAM'):
                    self.providerIAM = {}
                self.providerIAM["gcp"] = sa_obj["metadata"]["annotations"]["iam.gke.io/gcp-service-account"]


class MinimizedNode():
    def __init__(self, name, pods):
        self.name = name
        self.pods = pods

class MinimizedRole():
    def __init__(self, role):
        self.name = role["metadata"]["name"]
        if "namespace" in role["metadata"]: # crs granted via crbs have no ns
            self.namespace = role["metadata"]["namespace"] 
        self.rules = role["rules"]

