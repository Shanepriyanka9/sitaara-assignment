import os
import requests
from dotenv import load_dotenv

load_dotenv()

LINEAR_API_KEY = os.getenv("LINEAR_API_KEY")

url = "https://api.linear.app/graphql"

query = """
query {
  issues(first: 100) {
    nodes {
      id
      identifier
      title
      state {
        name
      }
      priority
      createdAt
      updatedAt
    }
  }
}
"""

headers = {
    "Authorization": LINEAR_API_KEY,
    "Content-Type": "application/json"
}

response = requests.post(
    url,
    json={"query": query},
    headers=headers,
    timeout=30
)

response.raise_for_status()
data = response.json()

if "errors" in data:
    print("Linear Error:", data["errors"])
    raise SystemExit(1)

issues = data["data"]["issues"]["nodes"]

for issue in issues:
    print(f"{issue['identifier']} | {issue['title']} | {issue['state']['name']}")