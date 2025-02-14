#!/usr/bin/env python

import os

from kubernetes import client, config
from kubernetes.config.kube_config import KUBE_CONFIG_DEFAULT_LOCATION

from helpers import timestamp
from resources import list_resources, watch_for_changes

METHOD = "METHOD"
UNIQUE_FILENAMES = "UNIQUE_FILENAMES"
SKIP_TLS_VERIFY = "SKIP_TLS_VERIFY"
FOLDER = "FOLDER"
FOLDER_ANNOTATION = "FOLDER_ANNOTATION"
LABEL = "LABEL"
LABEL_VALUE = "LABEL_VALUE"
RESOURCE = "RESOURCE"
REQ_PAYLOAD = "REQ_PAYLOAD"
REQ_URL = "REQ_URL"
REQ_METHOD = "REQ_METHOD"
SCRIPT = "SCRIPT"
URL_RETRY_ON = "URL_RETRY_ON"
URL_REFRESH_INTERVAL = "URL_REFRESH_INTERVAL"


def main():
    print(f"{timestamp()} Starting collector")

    folder_annotation = os.getenv(FOLDER_ANNOTATION)
    if folder_annotation is None:
        print(f"{timestamp()} No folder annotation was provided, "
              "defaulting to k8s-sidecar-target-directory")
        folder_annotation = "k8s-sidecar-target-directory"

    label = os.getenv(LABEL)
    if label is None:
        print(f"{timestamp()} Should have added {LABEL} as environment variable! Exit")
        return -1

    label_value = os.getenv(LABEL_VALUE)
    if label_value:
        print(f"{timestamp()} Filter labels with value: {label_value}")

    target_folder = os.getenv(FOLDER)
    if target_folder is None:
        print(f"{timestamp()} Should have added {FOLDER} as environment variable! Exit")
        return -1

    resources = os.getenv(RESOURCE, "configmap")
    resources = ("secret", "configmap") if resources == "both" else (resources,)
    print(f"{timestamp()} Selected resource type: {resources}")

    method = os.getenv(REQ_METHOD)
    url = os.getenv(REQ_URL)
    payload = os.getenv(REQ_PAYLOAD)
    script = os.getenv(SCRIPT)

    _initialize_kubeclient_configuration()

    unique_filenames = os.getenv(UNIQUE_FILENAMES)
    if unique_filenames is not None and unique_filenames.lower() == "true":
        print(f"{timestamp()} Unique filenames will be enforced.")
        unique_filenames = True
    else:
        print(f"{timestamp()} Unique filenames will not be enforced.")
        unique_filenames = False


    try:
        url_retry_on = [int(x) for x in os.getenv("URL_RETRY_ON", "500,502,503,504").split(",") if 500 <= int(x)<= 599]
        print(f"{timestamp()} 5xx content pulled disabled and retry enabled for {url_retry_on}")
    except ValueError:
        print(f"{timestamp()} cannot convert {os.getenv('URL_RETRY_ON')} elements to integer! Exit")
        return -1

    try:
        url_refresh_interval = int(os.getenv(URL_REFRESH_INTERVAL, 0))
    except ValueError:
        print(f"{timestamp()} cannot convert {URL_REFRESH_INTERVAL} to integer! Exit")
        return -1

    if url_refresh_interval > 0:
        print(f"{timestamp()} '.url' content refreshing will be enabled. Refresh interval {url_refresh_interval}")

    current_namespace = open("/var/run/secrets/kubernetes.io/serviceaccount/namespace").read()
    if os.getenv(METHOD) == "LIST":
        for res in resources:
            list_resources(label, label_value, target_folder, url, method, payload,
                           current_namespace, folder_annotation, res, unique_filenames, script, url_retry_on)
    else:
        watch_for_changes(os.getenv(METHOD), url_refresh_interval, label, label_value,
                          target_folder, url, method, payload, current_namespace, folder_annotation,
                          resources, unique_filenames, script, url_retry_on)


def _initialize_kubeclient_configuration():
    """
    Updates the default configuration of the kubernetes client. This is
    picked up later on automatically then.
    """

    # this is where kube_config is going to look for a config file
    kube_config = os.path.expanduser(KUBE_CONFIG_DEFAULT_LOCATION)
    if os.path.exists(kube_config):
        print(f"{timestamp()} Loading config from '{kube_config}'...")
        config.load_kube_config(kube_config)
    else:
        print(f"{timestamp()} Loading incluster config ...")
        config.load_incluster_config()

    if os.getenv(SKIP_TLS_VERIFY) == "true":
        configuration = client.Configuration.get_default_copy()
        configuration.verify_ssl = False
        configuration.debug = False
        client.Configuration.set_default(configuration)
    configuration = client.Configuration.get_default_copy()
    print(f"{timestamp()} Config for cluster api at '{configuration.host}' loaded...")


if __name__ == "__main__":
    main()
