#!/bin/bash
set -e
set -x

# Update package lists
sudo apt-get update -y

# Install prerequisite packages
sudo apt-get install -y apt-transport-https ca-certificates curl software-properties-common

# Disable swap
sudo swapoff -a
# Comment out swap entries in /etc/fstab
# Use a temporary file to avoid issues with sed directly modifying /etc/fstab in some environments
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

# Install Kubernetes components
sudo apt-get update -y
sudo apt-get install -y kubelet kubeadm kubectl

# Mark Kubernetes components to hold their version
sudo apt-mark hold kubelet kubeadm kubectl

# Enable and start kubelet
sudo systemctl enable kubelet
# Note: Kubelet might enter a crashloop until the cluster is initialized. This is expected.
# We will start it after kubeadm init or let kubeadm manage its start.
# For now, ensuring it's enabled is key. Kubeadm will start it.

echo "Kubelet enabled. Kubeadm will start it during init."

# Initialize Kubernetes cluster
# Using a common CIDR for Flannel. Can be parameterized later.
# Ensure the node IP is correctly identified by kubeadm or specify it if needed.
# Adding --ignore-preflight-errors=Swap for robustness in environments where swapoff might not be immediate
sudo kubeadm init --pod-network-cidr=10.244.0.0/16 --ignore-preflight-errors=Swap

# Set up kubeconfig for the user
mkdir -p $HOME/.kube
sudo cp -i /etc/kubernetes/admin.conf $HOME/.kube/config
sudo chown $(id -u):$(id -g) $HOME/.kube/config

# Install a Pod Network Add-on (Flannel)
# This requires kubectl to be configured, so it runs after setting up kubeconfig.
echo "Applying Flannel CNI..."
kubectl apply -f https://raw.githubusercontent.com/coreos/flannel/master/Documentation/kube-flannel.yml

echo "Master node installation script completed."

# Output the kubeadm join command
echo "To add worker nodes, use the following command:"
sudo kubeadm token create --print-join-command
