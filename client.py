# client.py
import requests, argparse

API_BASE = "http://127.0.0.1:8000"

def submit(api_key, command):
    # send as form data, with cookie for authentication
    r = requests.post(
        f"{API_BASE}/submit_command/",
        data={"command": command},
        cookies={"api_key": api_key},
        allow_redirects=False
    )
    print("Status Code:", r.status_code)
    if r.status_code == 302:
        print("Command submitted successfully!")
    else:
        print("Response:", r.text)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--key", required=True, help="Your API key")
    sub = parser.add_subparsers(dest="cmd")

    s1 = sub.add_parser("submit")
    s1.add_argument("command", help="Command to execute")

    args = parser.parse_args()

    if args.cmd == "submit":
        submit(args.key, args.command)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
