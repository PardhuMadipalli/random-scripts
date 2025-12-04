
export const handler = async (event) => {
    try {
        const IPO_URL = process.env.IPO_SOURCE_URL;   // e.g. https://example.com/ipo-list
        const NTFY_TOPIC = process.env.NTFY_TOPIC;     // e.g. myipoalerts
        const NTFY_URL = `https://ntfy.sh/${NTFY_TOPIC}`;

        // 1. Fetch IPO data
        const resp = await fetch(IPO_URL);
        if (!resp.ok) throw new Error(`Failed fetching IPO list: ${resp.status}`);

        const body = await resp.json();

        // 2. Parse depending on the response
        const ipoCalendarList = body.ipoCalendarList

        let ipoList = ''
        const istDate = new Date().getDate()

        for (const ipo of  ipoCalendarList) {
            if (ipo.cal_title.toLowerCase().includes('close') && ipo.cal_title.includes(istDate)) {
                ipoList += ipo.cal_date + ' - ' + ipo.cal_title + "\n"
            }
        }

        // if ipoList is empty
        if (ipoList.length === 0) {
            ipoList = 'No mainline IPO closes today'
        }

        // 3. Send IPO list to ntfy
        await fetch(NTFY_URL, {
            method: "POST",
            headers: {
                "Content-Type": "text/plain",
                "Title": "IPO List",
            },
            body: ipoList
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

console.log(await handler("nothing"))