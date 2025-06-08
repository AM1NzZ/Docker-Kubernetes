from flask import Flask, render_template, request, redirect, url_for, flash
import paramiko
import os

app = Flask(__name__)
# It's good practice to set a secret key for flash messages, though not strictly needed if not heavily used.
app.secret_key = os.urandom(24)

# Script paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MASTER_SCRIPT_PATH = os.path.join(BASE_DIR, 'scripts', 'master_install.sh')
WORKER_SCRIPT_PATH = os.path.join(BASE_DIR, 'scripts', 'worker_install.sh')


def ssh_connect(ip, username, password):
    """Establishes an SSH connection to the server."""
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        # Increased timeout for potentially slower connections during setup
        client.connect(ip, username=username, password=password, timeout=10)
        print(f"Successfully connected to {ip}")
        return client
    except Exception as e:
        print(f"Error connecting to {ip}: {e}")
        return None

def ssh_execute_command(client, command):
    """Executes a command on the remote server via SSH."""
    try:
        # Set a timeout for command execution, e.g., 15 minutes for long install scripts
        # The channel itself can have a timeout, or exec_command can.
        # Paramiko's exec_command timeout is for establishing the channel, not the command itself.
        # For long-running commands, we need to handle the stdout/stderr reading carefully.
        stdin, stdout, stderr = client.exec_command(command, timeout=900)

        # Reading stdout/stderr can block if the command produces a lot of output
        # or if it doesn't close the streams.
        stdout_output = stdout.read().decode('utf-8', errors='ignore')
        stderr_output = stderr.read().decode('utf-8', errors='ignore')
        exit_status = stdout.channel.recv_exit_status() # Wait for command to finish

        print(f"Command: {command}")
        # Limit printing large outputs to console for brevity in server logs
        print(f"Stdout (first 500 chars): {stdout_output[:500]}")
        print(f"Stderr (first 500 chars): {stderr_output[:500]}")
        print(f"Exit Status: {exit_status}")
        return stdout_output, stderr_output, exit_status
    except Exception as e:
        print(f"Error executing command '{command}': {e}")
        # Return the exception as stderr_output for more direct feedback
        return None, str(e), -1

def ssh_close_connection(client):
    """Closes the SSH connection."""
    if client:
        client.close()
        print("SSH connection closed.")

@app.route('/')
def index():
    results = request.args.getlist('results') # Get results if redirected
    return render_template('index.html', results=results)

@app.route('/install', methods=['POST'])
def install():
    results = []

    master_ip = request.form['master_ip']
    master_username = request.form['master_username']
    master_password = request.form['master_password']
    worker_ips_str = request.form.get('worker_ips', '') # Use .get for safety
    worker_username = request.form['worker_username']
    worker_password = request.form['worker_password']

    # Master Node Setup
    results.append(f"Attempting to connect to master node: {master_ip}")
    master_client = ssh_connect(master_ip, master_username, master_password)

    if master_client is None:
        results.append(f"Failed to connect to master node: {master_ip}")
        return render_template('index.html', results=results)

    results.append(f"Successfully connected to master node: {master_ip}")

    try:
        sftp = master_client.open_sftp()
        sftp.put(MASTER_SCRIPT_PATH, '/tmp/master_install.sh')
        sftp.close()
        results.append("Uploaded master_install.sh to master.")

        _stdout_val, _stderr_val, chmod_status = ssh_execute_command(master_client, 'chmod +x /tmp/master_install.sh')
        if chmod_status != 0:
            results.append(f"Failed to chmod script on master: {_stderr_val}")
            ssh_close_connection(master_client)
            return render_template('index.html', results=results)
        results.append("Made master_install.sh executable on master.")

        results.append("Executing master_install.sh on master... This may take a while (up to 15 mins).")
        master_stdout, master_stderr, master_exit_status = ssh_execute_command(master_client, 'sudo /tmp/master_install.sh')

        results.append(f"Master script stdout:\n{master_stdout}")
        results.append(f"Master script stderr:\n{master_stderr}")

        if master_exit_status != 0:
            results.append(f"Master script execution failed with exit status: {master_exit_status}")
            ssh_close_connection(master_client)
            return render_template('index.html', results=results)

        results.append("Master script executed successfully.")

        kubeadm_join_command = ""
        if master_stdout: # Ensure master_stdout is not None
            for line in master_stdout.splitlines():
                if 'kubeadm join' in line and '--token' in line:
                    kubeadm_join_command = line.strip() # Found the line
                    # Often the command is split over multiple lines, let's try to get the next line too if it starts with spaces
                    current_index = master_stdout.splitlines().index(line)
                    if current_index + 1 < len(master_stdout.splitlines()):
                        next_line = master_stdout.splitlines()[current_index+1].strip()
                        if next_line.startswith('--discovery-token-ca-cert-hash'): # Characteristic of the next line
                             kubeadm_join_command += " " + next_line
                    break

        if not kubeadm_join_command:
            results.append("ERROR: Could not find 'kubeadm join' command in master script output. Please check the master logs.")
            # Try to get it via command if master setup seemed to complete
            results.append("Attempting to retrieve join command directly...")
            join_cmd_stdout, join_cmd_stderr, join_cmd_status = ssh_execute_command(master_client, "sudo kubeadm token create --print-join-command")
            if join_cmd_status == 0 and join_cmd_stdout.strip():
                kubeadm_join_command = join_cmd_stdout.strip()
                results.append(f"Successfully retrieved join command: {kubeadm_join_command}")
            else:
                results.append(f"Failed to retrieve join command directly. Stdout: {join_cmd_stdout}, Stderr: {join_cmd_stderr}")
                ssh_close_connection(master_client)
                return render_template('index.html', results=results)

        results.append(f"Extracted/Retrieved join command: {kubeadm_join_command}")

    except Exception as e:
        results.append(f"An error occurred during master node setup: {str(e)}")
        ssh_close_connection(master_client)
        return render_template('index.html', results=results)
    finally:
        # Close master client if it hasn't been closed due to an error already
        # However, if we successfully got the join command, we need it open for workers if master == worker.
        # For now, let's close it here. If master is also a worker, it will be reconnected.
        if master_client: # Check if it's still a valid client object
             ssh_close_connection(master_client)


    # Worker Node Setup
    worker_ip_list = [ip.strip() for ip in worker_ips_str.split(',') if ip.strip()]
    if not worker_ip_list and not kubeadm_join_command:
        results.append("No worker IPs provided and no join command extracted. Assuming single-node cluster or manual worker addition.")
    elif not worker_ip_list and kubeadm_join_command:
        results.append("Master node setup complete. No worker IPs provided for automated setup.")
    elif not kubeadm_join_command: # Should have been caught earlier
        results.append("Critical error: No join command available for worker nodes.")
        return render_template('index.html', results=results)


    for worker_ip in worker_ip_list:
        results.append(f"--- Processing Worker Node: {worker_ip} ---")
        results.append(f"Attempting to connect to worker node: {worker_ip}")
        worker_client = ssh_connect(worker_ip, worker_username, worker_password)

        if worker_client is None:
            results.append(f"Failed to connect to worker node: {worker_ip}")
            continue

        results.append(f"Successfully connected to worker node: {worker_ip}")

        try:
            sftp_worker = worker_client.open_sftp()
            sftp_worker.put(WORKER_SCRIPT_PATH, '/tmp/worker_install.sh')
            sftp_worker.close()
            results.append(f"Uploaded worker_install.sh to {worker_ip}.")

            _stdout_val, _stderr_val, chmod_status_worker = ssh_execute_command(worker_client, 'chmod +x /tmp/worker_install.sh')
            if chmod_status_worker != 0:
                results.append(f"Failed to chmod script on {worker_ip}: {_stderr_val}")
                ssh_close_connection(worker_client)
                continue
            results.append(f"Made worker_install.sh executable on {worker_ip}.")

            results.append(f"Executing worker_install.sh on {worker_ip}... This may take a while.")
            # Ensure the join command is properly quoted when passed to the script
            worker_command = f"sudo /tmp/worker_install.sh \"{kubeadm_join_command}\""

            worker_stdout, worker_stderr, worker_exit_status = ssh_execute_command(worker_client, worker_command)

            results.append(f"Worker {worker_ip} script stdout:\n{worker_stdout}")
            results.append(f"Worker {worker_ip} script stderr:\n{worker_stderr}")

            if worker_exit_status != 0:
                results.append(f"Worker {worker_ip} script execution failed with exit status: {worker_exit_status}")
            else:
                results.append(f"Worker {worker_ip} script executed successfully.")

        except Exception as e:
            results.append(f"An error occurred during worker node {worker_ip} setup: {str(e)}")
        finally:
            if worker_client:
                ssh_close_connection(worker_client)
        results.append(f"--- Finished Processing Worker Node: {worker_ip} ---")

    results.append("All operations completed. Check status above.")
    return render_template('index.html', results=results)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
