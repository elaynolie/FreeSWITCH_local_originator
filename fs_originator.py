import paramiko
import os

def upload_and_originate(hostname, username, key_filename, destination, local_audio_path, remote_dir='/opt'):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(hostname, username=username, key_filename=key_filename, timeout=10)
        filename = os.path.basename(local_audio_path)
        remote_path = f'{remote_dir}/{filename}'

        # 1. Uploading file to remote server (SFTP)
        sftp = client.open_sftp()
        print(f'load {local_audio_path} -> {hostname}:{remote_path}')
        sftp.put(local_audio_path, remote_path)
        sftp.close()

        # 2. Converting to format compatible with FreeSWITCH (8000Hz, mono, 16-bit PCM)
        converted_path = remote_path.replace('.wav', '_conv.wav')
        conv_cmd = f'sox {remote_path} -r 8000 -c 1 -b 16 {converted_path}'
        stdin, stdout, stderr = client.exec_command(conv_cmd)
        stdout.channel.recv_exit_status()
        conv_err = stderr.read().decode('utf-8', errors='replace')
        if conv_err:
            print('sox stderr:', conv_err)

        # 3. Setting permissions (if freeswitch is not running under root)
        client.exec_command(f'chown freeswitch:freeswitch {converted_path}')

        # 4. originate call with playback of the already converted file
        cmd = f'fs_cli -x "originate {destination} &playback({converted_path})"'
        stdin, stdout, stderr = client.exec_command(cmd)
        out = stdout.read().decode('utf-8', errors='replace')
        err = stderr.read().decode('utf-8', errors='replace')

        print('STDOUT:', out)
        if err:
            print('STDERR:', err)

        return out
    finally:
        client.close()

upload_and_originate(
    '127.0.0.1', // ip address your workstation
    username='root', // username remote FS server
    key_filename='/root/.ssh/id_rsa', 
    destination='sofia/gateway/pstn/74951234578', //DID   
    local_audio_path='/Users/elaynolie/Downloads/audiofile.wav' ///audiofile on your workstation
)
