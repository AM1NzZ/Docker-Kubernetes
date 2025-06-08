# Kubernetes Web Installer

## Description
Kubernetes Web Installer is a Flask-based web application that provides a user interface to automate the installation of Kubernetes on a set of servers (one master, multiple workers) via SSH. It executes pre-defined shell scripts on the target machines to set up the cluster.

## Features
*   Web-based interface for providing server connection details (IPs, usernames, passwords).
*   Automated Kubernetes installation on a designated master node.
*   Automated Kubernetes installation on worker nodes and joining them to the master node's cluster.
*   Real-time feedback of the installation process displayed in the web UI.
*   Scripts for setting up `containerd`, `kubelet`, `kubeadm`, and `kubectl`.
*   Automatic installation of Flannel CNI on the master node.

## Prerequisites for the Machine Running the Flask App
*   Python 3.7+
*   `pip` (Python package installer)
*   Git (for cloning the repository)

## Prerequisites for the Target Servers (Master and Workers)
*   **Operating System:** Debian-based Linux distribution (e.g., Ubuntu 18.04, 20.04, 22.04). The scripts use `apt-get`.
*   **SSH Access:** Password-based SSH must be enabled.
*   **User Account:** An existing user account with `sudo` privileges is required. The application will use these credentials to connect and execute installation commands.
*   **Internet Access:** Target servers must have internet access to download Kubernetes packages and container images.
*   **Swap Disabled:** Kubernetes requires swap to be disabled. The installation scripts attempt to disable swap, but it's recommended to ensure it's off or can be turned off.
*   **Unique Hostnames:** (Recommended) Each node should have a unique hostname.
*   **Network Connectivity:** All nodes should be reachable from each other over the network. Firewalls might need adjustment for Kubernetes components (see Kubernetes documentation for port requirements).
*   **Resources:** Sufficient CPU, RAM, and disk space as per Kubernetes requirements for your cluster size.

## Setup and Installation (for the Flask App)

1.  **Clone the repository (if you haven't already):**
    ```bash
    # git clone <repository_url>
    # cd <repository_directory_name>
    ```
    (The application is expected to be in a directory, e.g., `k8s_installer_app_root/k8s_installer_app`)

2.  **Navigate to the application's root directory.** This is the directory containing `requirements.txt` and the `k8s_installer_app` subdirectory.

3.  **Create and activate a Python virtual environment:**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```
    (On Windows, use `venv\Scripts\activate`)

4.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

5.  **Run the application:**
    The application is started by running the `app.py` file located inside the `k8s_installer_app` subdirectory.
    ```bash
    python k8s_installer_app/app.py
    ```
    This will start the Flask development server.

6.  **Access the application:**
    Open your web browser and go to `http://<your-machine-ip>:5000` or `http://127.0.0.1:5000` if running locally (where `<your-machine-ip>` is the IP of the machine running the Flask app).

## How to Use
1.  Navigate to the web application in your browser.
2.  Carefully read the **Security Warnings** displayed on the page.
3.  Under "Master Node Configuration":
    *   Enter the IP address of your designated master node.
    *   Enter the username for SSH connection to the master node.
    *   Enter the password for the specified username on the master node.
4.  Under "Worker Nodes Configuration":
    *   Enter a comma-separated list of IP addresses for your worker nodes (e.g., `192.168.1.101,192.168.1.102`). Leave blank if you are setting up a single-node cluster or will add workers manually later.
    *   Enter the username for SSH connection to all worker nodes.
    *   Enter the password for the specified username on all worker nodes.
5.  Click the "Install Kubernetes" button.
6.  Monitor the installation progress in the "Installation Status" section that appears on the page. This section will show logs and results from the master and worker node setup processes.

## Important Security Considerations

*   **Experimental Tool:** **This tool is for experimental and educational purposes only. It is NOT recommended for production environments.** Use in a secure, isolated lab environment.
*   **Password-Based SSH:** This application uses password-based SSH authentication, which is inherently less secure than key-based authentication. Passwords are submitted through the web form and used by the backend to connect to your servers.
*   **Sudo Privileges:** The provided credentials must have `sudo` privileges on the target servers as the installation scripts require root access to install packages, modify system configurations, and initialize the Kubernetes cluster.
*   **Plain HTTP:** The Flask development server runs on HTTP by default, meaning all form data (including credentials) is transmitted unencrypted between your browser and the application server. **Do NOT use this tool over an untrusted network or expose the application server to the internet.**
*   **No Input Sanitization Beyond Defaults:** While standard Flask/Jinja defenses against common web vulnerabilities (like XSS) are generally active, the application's primary focus is not on robust input sanitization for all fields against all possible attack vectors. Be mindful of the data you enter.
*   **Review Scripts:** It is **highly recommended** to review the `k8s_installer_app/scripts/master_install.sh` and `k8s_installer_app/scripts/worker_install.sh` scripts thoroughly before running this application against any server to understand the commands that will be executed.
*   **Data Handling:** User credentials are processed in memory by the Flask application to establish SSH connections and are not explicitly stored by this application. However, ensure the environment where the Flask app runs is secure.

## Troubleshooting
*   **SSH Connection Failures:**
    *   Verify IP addresses, usernames, and passwords.
    *   Ensure the SSH server is running on target machines (`sudo systemctl status ssh`).
    *   Check if password authentication is enabled in `/etc/ssh/sshd_config` (`PasswordAuthentication yes`) on target nodes.
    *   Test SSH connection manually from the machine running the Flask app: `ssh user@host_ip`.
    *   Check network connectivity and firewalls (e.g., `ufw status` on targets).
*   **Script Execution Failures:**
    *   Carefully examine the `stdout` and `stderr` output provided in the "Installation Status" section in the UI. This often contains specific error messages from the scripts.
    *   Ensure all prerequisites for target servers are met (OS, internet access, sudo rights).
    *   If a script fails midway, the target machine might be in an inconsistent state. Manual cleanup or re-imaging might be necessary.
*   **`kubeadm init` or `kubeadm join` issues:**
    *   Check `/var/log/syslog` or use `journalctl -xe` on the target nodes for detailed logs from `kubelet` or `kubeadm`.
    *   Ensure the Pod Network CIDR (e.g., `10.244.0.0/16` for Flannel) does not conflict with your existing network.
*   **Python/Flask App Issues:**
    *   Ensure all dependencies in `requirements.txt` are installed in your virtual environment.
    *   Check the Flask development server console output for any Python errors.

## Disclaimer
Use this tool at your own risk. The author(s) and contributor(s) are not responsible for any damage, data loss, or system misconfiguration caused by its use. Always back up important data and test thoroughly in non-critical environments.
