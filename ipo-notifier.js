
export const handler = async (event) => {
    try {
        const IPO_URL = process.env.IPO_SOURCE_URL;   // e.g. https://example.com/ipo-list
        const NTFY_TOPIC = process.env.NTFY_TOPIC;     // e.g. myipoalerts
        const NTFY_URL = `https://ntfy.sh/${NTFY_TOPIC}`;

        // 1. Fetch IPO data
        let resp;
        let attempts = 0;
        const maxAttempts = 3;
        const delay = 2000; // 2 seconds

        while (attempts < maxAttempts) {
            try {
                resp = await fetch(IPO_URL);
                if (resp.ok) break;
                throw new Error(`HTTP ${resp.status}`);
            } catch (error) {
                attempts++;
                if (attempts >= maxAttempts) {
                    throw new Error(`Failed fetching IPO list after ${maxAttempts} attempts: ${error.message}`);
                }
                console.log(`Attempt ${attempts} failed, retrying in ${delay}ms...`);
                await new Promise(resolve => setTimeout(resolve, delay));
            }
        }

        const body = await resp.json();

        // 2. Parse depending on the response
        const ipoItems = body.data.items

        console.log('Fetched IPO list of size: ', ipoItems.length)

        let ipoList = []
        let ipoDetails = ''
        const date = getFormattedDate();
        console.log(`Formatted date is ${date}`)

        for (const ipo of  ipoItems) {
            console.log(`Checking IPO: ${ipo.ipo_type_tag}`)
            if (ipo.ipo_type_tag.includes('Mainboard')) {
                console.log(`Found mainline IPO: ${ipo.name}`)
                if (ipo.issue_end_date.includes(date)) {
                    ipoList.push(ipo.name.trim())
                    ipoDetails += ipo.name + ' - ' + ipo.issue_start_date + '-' + ipo.issue_end_date + "\n"        
                }
            }
        }

        let ipoListTitle = ''
        // if ipoList is empty
        if (ipoList.length === 0) {
            ipoListTitle = 'No mainline IPO closes today'
        } else {
            ipoListTitle = ipoList.join(', ')
            ipoListTitle = `${ipoListTitle} close today`
        }

        console.log(`Sending title as ${ipoListTitle}`)

        // 3. Send IPO list to ntfy
        await fetch(NTFY_URL, {
            method: "POST",
            headers: {
                "Content-Type": "text/plain",
                "Title": ipoListTitle,
            },
            body: ipoDetails || 'No mainline IPO closes today'
        });

        return {
            statusCode: 200,
            body: JSON.stringify({ message: "Sent IPO list to ntfy", count: ipoList.length })
        };

    } catch (err) {
        console.error("Error:", err);
        return {
            statusCode: 500,
            body: JSON.stringify({ error: err.message })
        };
    }
};

function getFormattedDate() {
    const date = new Date(); // Get the current date and time

    const day = date.getDate(); // Get the day of the month (1-31)
    const year = date.getFullYear(); // Get the full year (e.g., 2025)

    // Array of short month names
    const monthNames = [
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"
    ];
    const month = monthNames[date.getMonth()]; // Get the month name from the array

    return `${day} ${month} ${year}`; // Construct the formatted string
}

console.log(await handler("nothing"))