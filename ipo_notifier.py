import json
import os
import time
from datetime import datetime
import urllib.request
import urllib.parse


def lambda_handler(event, context):
    try:
        IPO_URL = os.environ['IPO_SOURCE_URL']  # e.g. https://example.com/ipo-list
        NTFY_TOPIC = os.environ['NTFY_TOPIC']   # e.g. myipoalerts
        NTFY_URL = f"https://ntfy.sh/{NTFY_TOPIC}"

        # 1. Fetch IPO data
        resp = None
        attempts = 0
        max_attempts = 3
        delay = 1  # 1 second

        while attempts < max_attempts:
            try:
                with urllib.request.urlopen(IPO_URL) as resp:
                    if resp.status == 200:
                        body = json.loads(resp.read().decode('utf-8'))
                        break
                    raise Exception(f"HTTP {resp.status}")
            except Exception as error:
                attempts += 1
                if attempts >= max_attempts:
                    raise Exception(f"Failed fetching IPO list after {max_attempts} attempts: {str(error)}")
                print(f"Attempt {attempts} failed, retrying in {delay}s...")
                time.sleep(delay)

        # 2. Parse depending on the response
        ipo_items = body['data']['items']

        print(f'Fetched IPO list of size: {len(ipo_items)}')

        ipo_list = []
        ipo_details = ''
        date = get_formatted_date()
        print(f"Formatted date is {date}")

        for ipo in ipo_items:
            # print(f"Checking IPO: {ipo['ipo_type_tag']}")
            if not 'SME' in ipo['ipo_type_tag']:
                # print(f"Found mainline IPO: {ipo['name']}")
                ipo_details += f"{ipo['name']} - {ipo['issue_start_date']}-{ipo['issue_end_date']}\n"
                if date in ipo['issue_end_date']:
                    ipo_list.append(ipo['name'].strip())

        # if ipo_list is empty
        if len(ipo_list) == 0:
            ipo_list_title = 'No mainline IPO closes today'
        else:
            ipo_list_title = ', '.join(ipo_list)
            ipo_list_title = f"{ipo_list_title} close today"

        print(f"Sending title as {ipo_list_title}")

        # 3. Send IPO list to ntfy
        data = (ipo_details or 'No mainline IPOs today').encode('utf-8')
        req = urllib.request.Request(
            NTFY_URL,
            data=data,
            headers={
                "Content-Type": "text/plain",
                "Title": ipo_list_title,
            },
            method='POST'
        )
        with urllib.request.urlopen(req) as response:
            pass  # We don't need the response

        return {
            'statusCode': 200,
            'body': json.dumps({'message': 'Sent IPO list to ntfy', 'count': len(ipo_list)})
        }

    except Exception as err:
        print(f"Error: {err}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(err)})
        }


def get_formatted_date():
    """Get the current date formatted as 'DD MMM YYYY'"""
    date = datetime.now()
    
    day = date.day
    year = date.year
    
    # Array of short month names
    month_names = [
        "Jan", "Feb", "Mar", "Apr", "May", "Jun",
        "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"
    ]
    month = month_names[date.month - 1]  # month is 1-indexed
    
    return f"{day} {month} {year}"


# Test the handler (equivalent to the console.log at the end)
if __name__ == "__main__":
    result = lambda_handler("nothing", None)
    print(result)