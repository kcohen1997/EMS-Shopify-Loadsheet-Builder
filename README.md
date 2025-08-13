# Eddie Motorsports Shopify Product Loadsheet

This repository creates a GUI cleaning up Eddie Motorsports product information from the e-commerce site Shopify. The resulting Loadsheet contains the following information:

* **Part #:**: taken from "Variant SKU" field
* **Full Title:**: taken from "Title", "Option1 Value", "Option2 Value" and "Option3 Value" fields
* **Category:**: taken from "Type" field
* **Handle:**: taken from "Handle" field
* **Title:**: title of parent product based on "Handle" field
* **Retail Price:**: taken from "Variant Price" field
* **Length (in):**: length of product (taken from custom "Length" metafield)
* **Width (in):**: width of product (taken from custom "Width" metafield)
* **Height (in):**: height of product (taken from custom "Height" metafield)
* **Weight (lb):**: weight of product (taken from custom "Weight" metafield)
* **Fitment:**: fitment of product (taken from custom "Fitment" metafield)
* **Description:**: taken from "HTML (Body)" metafield
* **Image Link:**: taken from "Variant Image" field
* **Product Link:**: combines Eddie Motorsports Website link with handle

To access the completed exe file, visit the "Release" section.

## How To Create Executable File

### Step 1: Download Product CSV File from Shopify and Python File From Repository (create_shopify_loadsheet.py)

If using sample csv file, download "shopify_sample_data.csv"

### Step 2: Download the following onto your computer:

#### Python (Programming Language): 

How To Download:

https://www.python.org/downloads/

Run this command in the terminal to see if downloaded properly:

```bash
python --version
```

pyinstaller --onefile --noconsole create_shopify_loadsheet.py

#### Pip (Python Package Manager):

How To Download:

pip install pyinstaller

Run this command in the terminal to see if downloaded properly:

```bash
pip --version
```

#### Pyinstaller (Converts Python Scripts Into Executable Files):

How To Download:

pip download pyinstaller

Run this command in the terminal to see if downloaded properly:

```bash
pyinstaller --version
```
### Step 3:  In terminal, go to the same folder/directory as the Python file and enter the following command:

```bash
pyinstaller --onefile --noconsole create_shopify_loadsheet.py
```
The resulting file will be located in the newly created "dist" folder
