import json
import subprocess

from base64 import b64decode


namespace = 'fora-dev'

SECRETS_MAP = {
    'redis': ['host', 'port'],
    'psql': ['host', 'port', 'user', 'password'],
    'aws-credentials': ['AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY'],
    'django': ['secret', 'deploy-url'],
    'rollbar': ['token'],
    'sqs': ['host'],
    'eth': ['network'],
    'slack': ['token'],
    'environment': ['name'],
    'sns': ['host'],
}

for secret_name in SECRETS_MAP:
    out = subprocess.Popen(
        ['kubectl', 'get', 'secret', '-n', namespace, secret_name, '-o', 'json'],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT
    )

    stdout, stderr = out.communicate()

    try:
        secret = json.loads(stdout)['data']
    except:  # noqa
        secret = {}

    print(secret_name)
    for key in SECRETS_MAP[secret_name]:
        current_value = b64decode(secret[key] if key in secret else '')
        current_value = current_value.decode('utf-8')

        display_value = f' ({current_value})' if current_value else ''
        value = input(f'{key}{display_value}: ')

        secret.update({key: value or current_value})

    literals = []
    for key, value in secret.items():
        literals.append(f'--from-literal={key}=\'{value}\'')