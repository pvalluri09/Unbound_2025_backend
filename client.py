# client.py
import requests, argparse

API_BASE = "http://127.0.0.1:8000"

def submit(api_key, command):
    r = requests.post(f"{API_BASE}/commands/", json={"command_text": command}, headers={"x-api-key": api_key})
    print("Status Code:", r.status_code)
    try:
        print("Response:", r.json())
    except:
        print("Response Text:", r.text)

def credits(api_key):
    r = requests.get(f"{API_BASE}/credits/", headers={"x-api-key": api_key})
    print("Status Code:", r.status_code)
    try:
        print("Response:", r.json())
    except:
        print("Response Text:", r.text)

def history(api_key):
    r = requests.get(f"{API_BASE}/history/", headers={"x-api-key": api_key})
    print("Status Code:", r.status_code)
    try:
        print("Response:", r.json())
    except:
        print("Response Text:", r.text)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--key", required=True)
    sub = parser.add_subparsers(dest="cmd")
    s1 = sub.add_parser("submit")
    s1.add_argument("command")
    sub.add_parser("credits")
    sub.add_parser("history")
    args = parser.parse_args()

    if args.cmd == "submit":
        submit(args.key, args.command)
    elif args.cmd == "credits":
        credits(args.key)
    elif args.cmd == "history":
        history(args.key)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
