#!/bin/bash
set -e
set -x

# Check if the join command is provided
if [ -z "$1" ]; then
    echo "Error: Kubeadm join command not provided."
    echo "Usage: $0 \"<kubeadm_join_command>\""
    exit 1
fi

JOIN_COMMAND=$1

# Update package lists
sudo apt-get update -y

# Install prerequisite packages
sudo apt-get install -y apt-transport-https ca-certificates curl software-properties-common

# Disable swap
sudo swapoff -a
# Comment out swap entries in /etc/fstab
sudo cp /etc/fstab /etc/fstab.bak
cat /etc/fstab.bak | grep -v 'swap' | sudo tee /etc/fstab > /dev/null

# Install container runtime (containerd)
sudo apt-get install -y containerd
sudo mkdir -p /etc/containerd
sudo containerd config default | sudo tee /etc/containerd/config.toml
sudo sed -i 's/SystemdCgroup = false/SystemdCgroup = true/g' /etc/containerd/config.toml
sudo systemctl restart containerd
sudo systemctl enable containerd

# Add Kubernetes APT repository and key
curl -s https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo apt-key add -
sudo apt-add-repository "deb http://apt.kubernetes.io/ kubernetes-xenial main"

# Install Kubernetes components (kubelet and kubeadm)
# kubectl is not strictly required on worker nodes but can be useful for debugging.
# For minimal setup, it can be omitted.
sudo apt-get update -y
sudo apt-get install -y kubelet kubeadm # kubectl

# Mark Kubernetes components to hold their version
sudo apt-mark hold kubelet kubeadm # kubectl

# Enable and start kubelet
sudo systemctl enable kubelet
# Kubelet will be started by kubeadm join or will restart after successful join.
echo "Kubelet enabled. Kubeadm will manage its state during join."

# Execute the kubeadm join command
echo "Attempting to join the Kubernetes cluster..."
# Adding --ignore-preflight-errors=Swap for robustness
# Ensure the JOIN_COMMAND is quoted if it contains spaces, although it should be passed as a single arg.
sudo bash -c "$JOIN_COMMAND --ignore-preflight-errors=Swap"

echo "Worker node installation script completed."
echo "Node should now be part of the Kubernetes cluster. Verify on the master node with 'kubectl get nodes'."
