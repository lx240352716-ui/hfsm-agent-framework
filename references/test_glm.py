"""Quick test: GLM API with JWT auth."""
import time, json, jwt
from openai import OpenAI

# Generate JWT
key_id = '5470fc1666d94f86b260533a2b142356'
secret = 'C2MzrWJxSUPE7KHE'
payload = {
    'api_key': key_id,
    'exp': int(time.time()) + 3600,
    'timestamp': int(time.time()),
}
token = jwt.encode(payload, secret, algorithm='HS256',
                   headers={'alg': 'HS256', 'sign_type': 'SIGN'})
print(f'JWT: {token[:30]}...')

# Call GLM
client = OpenAI(
    api_key=token,
    base_url='https://open.bigmodel.cn/api/paas/v4',
)
print('Calling GLM-4-Plus...')
r = client.chat.completions.create(
    model='glm-4-plus',
    messages=[{'role': 'user', 'content': '用一句话介绍你自己'}],
    max_tokens=50,
    timeout=15,
)
print(f'OK: {r.choices[0].message.content}')
