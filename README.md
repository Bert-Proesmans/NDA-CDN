# NDA - CDN project

## Sync

This tool listens for filesystem events and will upload new/updated files to the cloud.


## App

Webserver code which acts as a CDN. The code takes a variable (provided within URL) identifying
a resource uploaded by the **Sync** tool and proxies it back to the user.
