import json
import os
import time
import re
import logging
from datetime import datetime
import urllib.request
import urllib.parse

# Configure logging based on environment
logger = logging.getLogger()

log_level = os.environ.get('log_level', 'DEBUG')

# Source - https://stackoverflow.com/a/56579088
# Posted by Pit
# Retrieved 2025-12-29, License - CC BY-SA 4.0
if logging.getLogger().hasHandlers():
    # The Lambda environment pre-configures a handler logging to stderr. If a handler is already configured,
    # `.basicConfig` does not execute. Thus we set the level directly.
    logging.getLogger().setLevel(log_level)
else:
    logging.basicConfig(level=log_level, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s') # non lambda environments


def get_gmp_data():
    """
    Fetch GMP data from the specified URL and parse company names and GMP values.
    Returns a consolidated string with company names and their GMP values.
    """
    GMP_DATA_URL = os.environ['GMP_DATA_URL']
    
    try:
        logger.debug(f"Checking the URL {GMP_DATA_URL}")
        # Make GET request with browser-like headers to avoid 403 Forbidden
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': 'https://webnodejs.investorgain.com/'
        }
        
        req = urllib.request.Request(GMP_DATA_URL, headers=headers)
        with urllib.request.urlopen(req) as response:
            if response.status != 200:
                return "Error: Failed to fetch GMP data"
            
            data = json.loads(response.read().decode('utf-8'))
            logger.debug(f"Fetched GMP data response: {data}")
        
        # Extract reportTableData array
        report_data = data.get('reportTableData', [])
        
        if not report_data:
            return "No GMP data available"
        
        # Parse and clean the data
        gmp_info = []
        
        for item in report_data:
            # Use clean field names
            company_name = item.get('~ipo_name', '').strip()
            gmp_percent = item.get('~gmp_percent_calc', '')
            closing_date = item.get('Close', '').split('<', 1)[0]
            
            if company_name and gmp_percent:
                gmp_info.append(f"- {company_name} (Closing on {closing_date}) - GMP: {gmp_percent}%")
        
        if not gmp_info:
            return "No valid GMP data found"
        
        # Consolidate into a single string
        return "\n".join(gmp_info)
        
    except Exception as e:
        logger.error(f"Exception occurred while fetching GMP data: {str(e)}")
        return f"Error fetching GMP data: {str(e)}"

def get_closing_ipo_data(is_sme: bool = False) -> (str, str):
    IPO_URL = os.environ['IPO_SOURCE_URL']  # e.g. https://example.com/ipo-list

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
            logger.warning(f"Attempt {attempts} failed, retrying in {delay}s...")
            time.sleep(delay)

    # 2. Parse depending on the response
    ipo_items = body['data']['items']

    logger.debug(f'Fetched IPO list of size: {len(ipo_items)}')

    ipo_list = []
    ipo_details = ''
    date = get_formatted_date()
    logger.debug(f"Formatted date is {date}")

    for ipo in ipo_items:
        # logger.debug(f"Checking IPO: {ipo['ipo_type_tag']}")
        if not 'SME' in ipo['ipo_type_tag']:
            # logger.debug(f"Found mainline IPO: {ipo['name']}")
            ipo_details += f"{ipo['name']} - {ipo['issue_start_date']}-{ipo['issue_end_date']}\n"
            if date in ipo['issue_end_date']:
                ipo_list.append(ipo['name'].strip())

    # if ipo_list is empty
    if len(ipo_list) == 0:
        ipo_list_title = 'No mainline IPO closes today'
    else:
        ipo_list_title = ', '.join(ipo_list)
        ipo_list_title = f"{ipo_list_title} close today"

    logger.debug(f"Sending title as {ipo_list_title}")

    # 3. Send IPO list to ntfy
    data = (ipo_details or 'No mainline IPOs open today')
    return (ipo_list_title, data)

def get_priority(ipo_list_title: str, ipo_details: str) -> int:
    if not 'No mainline' in ipo_list_title:
        return 5 # Some IPO is closing today. Highest priority
    if 'No mainline' in ipo_details:
        return 1 # No IPOs open today. Lowest priority
    return 3 # default priority when IPOs are open, but nothing is closing today


def lambda_handler(event, context):
    NTFY_TOPIC = os.environ['NTFY_TOPIC']   # e.g. myipoalerts
    NTFY_URL = f"https://ntfy.sh/{NTFY_TOPIC}"
    try:
        ipo_list_title, data = get_closing_ipo_data()
        priority = get_priority(ipo_list_title, data)
        tags = "rotating_light" if priority == 5 else "warning" if priority == 3 else "info"
        data += "\n\nGMP data:\n" + get_gmp_data()
        req = urllib.request.Request(
            NTFY_URL,
            data=data.encode('utf-8'),
            headers={
                "Content-Type": "text/plain",
                "Title": ipo_list_title,
                "Tags": tags,
                "Priority": str(priority),
                "Markdown": "yes",
                "Actions": "view,Open Chittorgarh,https://www.chittorgarh.com/ipo/ipo_dashboard.asp,clear=false"
            },
            method='POST'
        )
        with urllib.request.urlopen(req) as response:
            pass  # We don't need the response

        return {
            'statusCode': 200,
            'body': json.dumps({'message': 'Sent IPO list to ntfy'})
        }

    except Exception as err:
        logger.error(f"Error: {err}")
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
    logger.info(lambda_handler("", ""))