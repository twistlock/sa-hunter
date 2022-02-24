#!/usr/bin/env python3
"""
Finds the permissions of service accounts used by pods.
Note that clusterroles are shown without a namespace, unless assigned through a rolebinding.
"""

from minimized_objs import MinimizedServiceAccount, MinimizedRole, MinimizedNode, UnsortableStr
from kubernetes import client, config
from sys import argv
import argparse
import json
from typing import Dict, List

def main(args):
    config.load_kube_config()
    core_client = client.CoreV1Api()
    rbac_client = client.RbacAuthorizationV1Api()

    # Build sa_map, a dictionary of serviceaccounts to inspect. 
    # sa_map maps between SA full names to their corresponding MinimizedServiceAccount object
    used_sa_to_node_map = build_used_sas_to_node_map(core_client)
    sa_map = build_serviceaccount_map(core_client, used_sa_to_node_map, args.all_sas)
    if not sa_map or len(sa_map.keys()) == 0: 
        print("[!] No service accounts to look into")
        return 

    # Get Roles, ClusterRoles, RoleBindings and ClusterRoleBindings
    roles, cluster_roles = get_roles(rbac_client)
    if not roles or not cluster_roles:
        print("[!] Failed to retrieve roles or clusterroles")
        return
    rbs, crbs = get_bindings(rbac_client)
    if not rbs or not crbs:
        print("[!] Failed to retrieve rbs or crbs")
        return

    # Populate permissions granted via rolebindings
    populate_rolebindings_permissions_for_sas(sa_map, roles, cluster_roles, rbs)
    # Populate permissions granted via clusterrolebindings
    populate_clusterrolebindings_permissions_for_sas(sa_map, cluster_roles, crbs)

    # Output results
    sa_results = list(sa_map.values())
    node_data = map_nodes_to_sa_fullname(sa_results)
    hunt_results = {
        UnsortableStr("metadata") : get_metadata(),
        UnsortableStr("serviceaccounts"): sa_results,
        UnsortableStr("nodes"): node_data
    } 
    output = json.dumps(hunt_results, indent=4, sort_keys=True, default=vars)    
    if not args.out_file or args.loud_mode:
        print(output)
    if args.out_file:
        with open(args.out_file, "w") as outf:
            outf.write(output)

# Map used serviceaccounts to MinimizedNodes
def build_used_sas_to_node_map(core_client) -> Dict[str, MinimizedNode]:
    sa_to_node = {}
    response = core_client.list_pod_for_all_namespaces(watch=False, _preload_content=False)
    pods_resp = json.loads(response.data)

    for pod_obj in pods_resp["items"]:
        if "serviceAccountName" in pod_obj["spec"]:
            sa = f"{pod_obj['metadata']['namespace']}:{pod_obj['spec']['serviceAccountName']}"
            if sa not in sa_to_node.keys():
                # New service account
                if 'nodeName' in pod_obj['spec']:
                    nodename = pod_obj['spec']['nodeName']
                else:
                    nodename = None
                sa_to_node[sa] = [MinimizedNode(nodename, [pod_obj['metadata']['name']])]
            else:
                # Already seen this service acconut
                new_node_for_sa = True
                if 'nodeName' in pod_obj['spec']:
                    nodename = pod_obj['spec']['nodeName']
                else:
                    nodename = None
                for existing_node in sa_to_node[sa]:
                    if nodename == existing_node.name:
                       existing_node.pods.append(pod_obj['metadata']['name'])
                       new_node_for_sa = False
                       break
                if new_node_for_sa:
                    sa_to_node[sa].append(MinimizedNode(nodename, [pod_obj['metadata']['name']]))
    return sa_to_node

# Map serviceaccounts fullnames to MinimizedServiceAccounts
def build_serviceaccount_map(core_client, used_sa_to_node_map, all_sas:bool) -> Dict[str, MinimizedServiceAccount]:
    sa_map = {}
    response = core_client.list_service_account_for_all_namespaces(watch=False, _preload_content=False)
    sa_resp = json.loads(response.data)
    sanity_counter = 0

    for sa in sa_resp["items"]:
        sa_fullname = f"{sa['metadata']['namespace']}:{sa['metadata']['name']}"
        if sa_fullname not in used_sa_to_node_map.keys():
            if all_sas:
                sa_map[sa_fullname] = MinimizedServiceAccount(sa)
        else:
            sanity_counter += 1
            sa_map[sa_fullname] = MinimizedServiceAccount(sa, used_sa_to_node_map[sa_fullname])
    
    if len(used_sa_to_node_map.keys()) != sanity_counter:
        # Sanity check verifying we found all SAs that are used by pods
        print("[!] Didn't find some service accounts which are used by pods")
        return None
    return sa_map


def get_bindings(rbac_client):
    response = rbac_client.list_cluster_role_binding(watch=False, _preload_content=False)
    crb_resp = json.loads(response.data)
    response = rbac_client.list_role_binding_for_all_namespaces(watch=False, _preload_content=False)
    rb_resp = json.loads(response.data)
    return rb_resp["items"], crb_resp["items"]


def get_roles(rbac_client):
    response = rbac_client.list_cluster_role(watch=False, _preload_content=False)
    cluster_roles_resp = json.loads(response.data)
    response = rbac_client.list_role_for_all_namespaces(watch=False, _preload_content=False)
    roles_resp = json.loads(response.data)
    return roles_resp["items"], cluster_roles_resp["items"]


def populate_rolebindings_permissions_for_sas(sa_map, roles, cluster_roles, rbs):
    # Go over role bindings
    for rb in rbs:
        if "subjects" not in rb or "roleRef" not in rb:
            continue
        minimized_sas = get_relevant_subjects(rb, sa_map)

        if rb['roleRef']['kind'] == 'ClusterRole':
            role = next((cr for cr in cluster_roles if cr["metadata"]["name"] == rb["roleRef"]["name"]), None)
            if not role:
                continue # no such cluster role
            role["metadata"]["namespace"] = rb["metadata"]["namespace"] # crs assgined via rbs are namespace scoped
        else:
            roleRef_ns = rb['metadata']['namespace']
            if "namespace" in rb['roleRef']: # roleRef doesn't necessarily hold ns info
                roleRef_ns = rb['roleRef']['namespace']
            role = next((role for role in roles if \
                    role["metadata"]["name"] == rb["roleRef"]["name"] and \
                    role["metadata"]["namespace"] == roleRef_ns), None)   
            if not role:
                continue # no such role 
        
        for minimized_sa in minimized_sas:
            minimized_sa.roles.append(MinimizedRole(role))
            

def populate_clusterrolebindings_permissions_for_sas(sa_map, cluster_roles, crbs):
    for crb in crbs:
        if "subjects" not in crb or "roleRef" not in crb:
            continue
        minimized_sas = get_relevant_subjects(crb, sa_map)

        cluster_role = next((cr for cr in cluster_roles if cr["metadata"]["name"] == crb["roleRef"]["name"]), None)
        if not cluster_role:
            continue # no such cluster role

        for minimized_sa in minimized_sas:
            minimized_sa.roles.append(MinimizedRole(cluster_role))
            
            
# Returns a list of MinimizedServiceAccounts refrenced by the crb/rb
def get_relevant_subjects(rb, sa_map):
    relevant_minimized_sas = []
    for subject in rb["subjects"]:
        # Handle ServiceAccount subjects
        if subject["kind"] == "ServiceAccount":
            if "namespace" not in subject:
                subject["namespace"] = rb['metadata']['namespace']  # namespaceless rolebinding sa subjects seen in GKE
            sa_subject_fullname = f"{subject['namespace']}:{subject['name']}"
            if sa_subject_fullname in sa_map.keys():
                relevant_minimized_sas.append(sa_map[sa_subject_fullname])
        
        # Handle Group subjects
        elif subject["kind"] == "Group":
            grp = subject["name"]
            if not grp.startswith('system:serviceaccounts'):
                continue # only handle sa groups
            if grp == 'system:serviceaccounts':
                relevant_minimized_sas = list(sa_map.values())
            else:
                for sa_fullname in sa_map.keys():
                    if grp == f"system:serviceaccounts:{sa_fullname.split(':')[0]}":
                        relevant_minimized_sas.append(sa_map[sa_fullname])   
    
    return relevant_minimized_sas


def map_nodes_to_sa_fullname(minimized_sa_list:List[MinimizedServiceAccount]) -> List[Dict[str, str]]:
    node_to_sa_map = {}
    for minimized_sa in minimized_sa_list:
        for node in minimized_sa.nodes:
            if node.name not in node_to_sa_map.keys():
                if node.name != None:
                    node_to_sa_map[node.name] = {
                        "name": node.name, 
                        "serviceaccounts": [minimized_sa.fullname()]
                    }
            else:
                node_to_sa_map[node.name]["serviceaccounts"].append(minimized_sa.fullname())
    return list(node_to_sa_map.values())


def get_metadata():
    return {
        "platform": get_platform(),
        "cluster": get_cluster_name()
    }
    

def get_platform():
    version_client = client.VersionApi()
    version_info = version_client.get_code()
    for platfrom, identifier in {"eks": "-eks-", "gke": "-gke."}.items():
        if identifier in version_info.git_version:
            return platfrom
    return ""

def get_cluster_name():
    # returns a tuple of (all_contexts, current)
    current_context = config.list_kube_config_contexts()[1]
    if "context"  in current_context:
        if "cluster" in current_context["context"]:
            return current_context["context"]["cluster"]
    return ""

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="""Correlates serviceaccounts and pods to the permissions granted to them via rolebindings and clusterrolesbindings.
""")
    parser.add_argument('-a', dest='all_sas', action='store_true', help="show all service accounts, not only those assigned to a pod")
    parser.add_argument('-o', dest='out_file', action='store', help="save results to output file")
    parser.add_argument('-l', dest='loud_mode', action='store_true', help="loud mode, print results regardless of -o")
    parser.set_defaults(all_sas=False, out_file="", loud_mode=False)

    args = parser.parse_args()
    main(args)
