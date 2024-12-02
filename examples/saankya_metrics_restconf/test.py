import paramiko
import os

# Server credentials
hostname = '10.197.75.220'
port = 22
username = 'root'
password = 'smarts@123'
remote_directory = '/root/tharun/NETCONF-PM'

# Local directory to save files
local_directory = '/Users/ktharun/Desktop/PMFILES'

# Create SSH client
ssh_client = paramiko.SSHClient()
ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    # Connect to the server
    ssh_client.connect(hostname=hostname, port=port, username=username, password=password)

    # Create SCP client
    scp_client = ssh_client.open_sftp()

    # Change directory on the server
    scp_client.chdir(remote_directory)

    # Get list of files in the directory
    files = scp_client.listdir()

    # Create local directory if it doesn't exist
    if not os.path.exists(local_directory):
        os.makedirs(local_directory)

    # Copy files from server to local directory
    for file in files:
        remote_path = os.path.join(remote_directory, file)
        local_path = os.path.join(local_directory, file)
        scp_client.get(remote_path, local_path)
        print(f"File {file} copied successfully.")

    # Close SCP client
    scp_client.close()

    print("All files copied successfully.")
except Exception as e:
    print(f"Error: {e}")
finally:
    # Close SSH client
    ssh_client.close()
