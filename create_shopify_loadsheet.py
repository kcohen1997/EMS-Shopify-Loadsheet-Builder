# --- Import necessary libraries ---
import pandas as pd
import tkinter as tk
from tkinter import filedialog, messagebox
import chardet
import threading

# --- Validation: Allow only valid float values in text entries ---
def validate_float_input(new_value):
    if new_value == "":
        return True
    try:
        float(new_value)
        return True
    except ValueError:
        return False

# --- Add placeholder text to entry fields ---
def add_placeholder(entry, text):
    entry.configure(validate="none")
    
    if not entry.get():
        entry.insert(0, text)
        entry.config(fg="gray")

    def on_focus_in(event):
        if entry.get() == text:
            entry.delete(0, tk.END)
            entry.config(fg="black")

    def on_focus_out(event):
        if not entry.get():
            entry.insert(0, text)
            entry.config(fg="gray")

    entry.bind("<FocusIn>", on_focus_in)
    entry.bind("<FocusOut>", on_focus_out)

    # Re-enable validation
    entry.configure(validate="key")

def build_full_title(row):
    base_title = str(row.get('Title', '')).strip()
    options = []
    for opt_key in ['Option1 Value', 'Option2 Value', 'Option3 Value']:
        val = row.get(opt_key)
        if pd.notna(val):
            val_str = str(val).strip()
            if val_str and val_str.lower() != 'default title':
                options.append(val_str)
    return f"{base_title} - {' - '.join(options)}" if options else base_title

# --- Core file processing logic that runs in a background thread ---
def _process_file_worker(file_path):
    try:

        # Step 1: Read CSV File
        with open(file_path, 'rb') as f:
            raw_data = f.read()
            encoding = chardet.detect(raw_data)['encoding']

        df = pd.read_csv(file_path, encoding=encoding, low_memory=False)

        # Step 2: Forward-fill specific columns
        df['Title'] = df['Title'].ffill().infer_objects(copy=False)
        df['Published'] = df['Published'].infer_objects().ffill().infer_objects(copy=False)
        df['Status'] = df['Status'].ffill().infer_objects(copy=False)
        if 'Fitment (product.metafields.convermax.fitment)' in df.columns and 'Handle' in df.columns: # Forward-fill Fitment based on handle
            df['Handle'] = df['Handle']
            df['Fitment (product.metafields.convermax.fitment)'] = df.groupby('Handle')['Fitment (product.metafields.convermax.fitment)'].ffill().infer_objects(copy=False)
        if 'Type' in df.columns and 'Handle' in df.columns:
            df['Type'] = ( df.groupby('Handle')['Type'].ffill().infer_objects(copy=False))
        if 'Length (product.metafields.custom.length)' in df.columns and 'Handle' in df.columns:
            df['Length (product.metafields.custom.length)'] = ( df.groupby('Handle')['Length (product.metafields.custom.length)'].ffill().infer_objects(copy=False))
        if 'Width (product.metafields.custom.width)' in df.columns and 'Handle' in df.columns:
            df['Width (product.metafields.custom.width)'] = ( df.groupby('Handle')['Width (product.metafields.custom.width)'].ffill().infer_objects(copy=False))
        if 'Height (product.metafields.custom.height)' in df.columns and 'Handle' in df.columns:
            df['Height (product.metafields.custom.height)'] = ( df.groupby('Handle')['Height (product.metafields.custom.height)'].ffill().infer_objects(copy=False))

        # Step 3: Only include Published and Active Products
        df = df[
            (df['Variant Price'] > 0) &
            (df['Published'].astype(str).str.lower() == 'true') &
            (df['Status'].astype(str).str.lower() == 'active')
        ]

        # Step 4: Add Full Title based on Variant Options
        df['Full Title'] = df.apply(build_full_title, axis=1)

        # Step 5: Add Multipliers
        try:
            jobber_multiplier = float(jobber_price_entry.get()) if jobber_price_entry.get() else 0.85 # get multiplers from text input
            dealer_multiplier = float(dealer_price_entry.get()) if dealer_price_entry.get() else 0.75
            oemwd_multiplier = float(oemwd_price_entry.get()) if oemwd_price_entry.get() else 0.675
        except ValueError:
            root.after(0, lambda: [
                status_label.config(text="Error: Invalid multiplier"),
                messagebox.showerror("Input Error", "Please enter valid numeric values for multipliers."),
            ])
            return
        df['Jobber Price'] = round(df['Variant Price'] * jobber_multiplier, 2) # calculate prices based on multipliers
        df['Dealer Price'] = round(df['Variant Price'] * dealer_multiplier, 2)
        df['OEM/WD Price'] = round(df['Variant Price'] * oemwd_multiplier, 2)
        price_columns = ['Variant Price', 'Jobber Price', 'Dealer Price', 'OEM/WD Price'] # convert prices to currency
        for col in price_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce') \
                    .map(lambda x: f"${x:,.2f}" if pd.notnull(x) else "")

        # Step 6: Convert variant grams to weight
        df['Weight (lb)'] = round(df['Variant Grams'] * 0.00220462, 2)

        # Step 7: Clean 'Fitment' column by replacing '|' with space and newlines with comma + space
        if 'Fitment (product.metafields.convermax.fitment)' in df.columns:
            df['Fitment (product.metafields.convermax.fitment)'] = (
                df['Fitment (product.metafields.convermax.fitment)']
                .fillna('#N/A')
                .astype(str)
                .str.replace('|', ' ', regex=False)
                .str.replace('\n', ', ', regex=False)
            )

        # Step 8: Clean 'Length', 'Width', and 'Height' columns by removing the ' character
        for dim_col in ['Length (product.metafields.custom.length)', 'Width (product.metafields.custom.width)', 'Height (product.metafields.custom.height)']:
            if dim_col in df.columns:
                df[dim_col] = df[dim_col].fillna('#N/A').astype(str).str.replace("'", '', regex=False)

        # Step 9: Add product link based on handle
        df['Product Link'] = 'https://eddiemotorsports.com/products/' + df['Handle'].astype(str)
        
        # Step 10: Extract Image 2 and Image 3 based on Handle + Variant SKU + Image Position
        if {'Handle', 'Variant SKU', 'Image Position', 'Image Src'}.issubset(df.columns):
            df['Image Position'] = pd.to_numeric(df['Image Position'], errors='coerce')
    
        image_df = df[['Handle', 'Variant SKU', 'Image Position', 'Image Src']].dropna(subset=['Image Src'])    # Filter and sort image entries
        image_df = image_df.sort_values(['Handle', 'Variant SKU', 'Image Position'])
        image_groups = image_df.groupby(['Handle', 'Variant SKU'])['Image Src'].apply(list).to_dict() # Group by both Handle and Variant SKU
  
        df['Image 2'] = df.apply(lambda row: get_image(image_groups.get((row['Handle'], row['Variant SKU'])), 1), axis=1)   # Map Image 2 and 3 using (Handle, Variant SKU)
        df['Image 3'] = df.apply(lambda row: get_image(image_groups.get((row['Handle'], row['Variant SKU'])), 2), axis=1)

        df['Product Link'] = df['Handle'].astype(str).apply(lambda h: f'=HYPERLINK("https://eddiemotorsports.com/products/{h}")')
        df.rename(columns={ 'Variant Image': 'Image 1'}, inplace=True) # rename variant image to image 1
        df['Image 1'] = df['Image 1'].fillna('#N/A').astype(str).apply(lambda h: f'=HYPERLINK("{h}")' if h != '#N/A' else '#N/A')
        df['Image 2'] = df['Image 2'].fillna('#N/A').astype(str).apply(lambda h: f'=HYPERLINK("{h}")' if h != '#N/A' else '#N/A')
        df['Image 3'] = df['Image 3'].fillna('#N/A').astype(str).apply(lambda h: f'=HYPERLINK("{h}")' if h != '#N/A' else '#N/A')

        # Step 11: Create final column list
        final_variant_list = df.copy()
        final_column_list = [
            'Variant SKU', 'Full Title', 'Type', 'Handle', 'Title',  'Variant Price', 'Jobber Price',
            'Dealer Price', 'OEM/WD Price', 'Length (product.metafields.custom.length)', 'Width (product.metafields.custom.width)', 'Height (product.metafields.custom.height)',
            'Weight (lb)', 'Fitment (product.metafields.convermax.fitment)',
            'Body (HTML)', 'Image 1', 'Image 2', 'Image 3', 'Product Link'
        ]
        for col in final_column_list: # if column is not on csv file, fill in with '#N/A' so the column will at least exist
            if col not in final_variant_list.columns:
                final_variant_list[col] = '#N/A'
        final_variant_list = final_variant_list[final_column_list] # only include columns from column list
        final_variant_list.rename(columns={ # rename specific columns 
            'Variant SKU': 'Part #',
            'Type': 'Category',
            'Variant Price': 'Retail Price',
            'Length (product.metafields.custom.length)': 'Length (in)',
            'Width (product.metafields.custom.width)': 'Width (in)', 
            'Height (product.metafields.custom.height)': 'Height (in)',
            'Fitment (product.metafields.convermax.fitment)': 'Fitment',
            'Body (HTML)': 'Description',
            'Variant Image': 'Image 1',
        }, inplace=True)

        # Step 12: Fill any empty fields with '#N/A'
        final_variant_list.fillna("#N/A", inplace=True)

        # Step 13: Save the final processed CSV
        output_file_path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv")])
        if output_file_path:
            final_variant_list.to_csv(output_file_path, index=False)
            root.after(0, lambda: [
                status_label.config(text="Processing complete."),
                messagebox.showinfo("Success", f"File processed and saved as {output_file_path}"),
            ])
        else:
            root.after(0, lambda: [
                status_label.config(text="Save cancelled."),
            ])

    except Exception as e:
        root.after(0, lambda: [
            status_label.config(text=f"Error: {e}"),
            messagebox.showerror("Error", f"An error occurred:\n{e}"),
        ])

def hyperlink_image(url):
    if url and url != '#N/A':
        return f'=HYPERLINK("{url}", "{url}")'
    return '#N/A'

def process_file(file_path):
    status_label.config(text="Processing...")
    threading.Thread(target=_process_file_worker, args=(file_path,), daemon=True).start()

def select_file():
    file_path = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv")])
    if file_path:
        process_file(file_path)

def get_image(images, idx): # Helper to extract image by index safely
    try:
        return images[idx]
    except (IndexError, TypeError):
        return '#N/A'
            
# --- GUI setup ---
root = tk.Tk()
root.title("Shopify CSV Processor (EMS)")

# --- Frame for multiplier entries ---
entry_frame = tk.Frame(root)
entry_frame.pack(padx=20, pady=20)

vcmd = (root.register(validate_float_input), '%P')

# --- Multiplers ---
tk.Label(entry_frame, text="Jobber Price Multiplier:").grid(row=0, column=0, sticky="e")
jobber_price_entry = tk.Entry(entry_frame, validate="key", validatecommand=vcmd)
jobber_price_entry.grid(row=0, column=1, padx=(10, 10), pady=5)
add_placeholder(jobber_price_entry, "0.85")

tk.Label(entry_frame, text="Dealer Price Multiplier:").grid(row=1, column=0, sticky="e")
dealer_price_entry = tk.Entry(entry_frame, validate="key", validatecommand=vcmd)
dealer_price_entry.grid(row=1, column=1, padx=(10, 10), pady=5)
add_placeholder(dealer_price_entry, "0.75")

tk.Label(entry_frame, text="OEM/WD Price Multiplier:").grid(row=2, column=0, sticky="e")
oemwd_price_entry = tk.Entry(entry_frame, validate="key", validatecommand=vcmd)
oemwd_price_entry.grid(row=2, column=1, padx=(10, 10), pady=5)
add_placeholder(oemwd_price_entry, "0.675")

# --- Process Button ---
process_button = tk.Button(root, text="Select and Process CSV File", command=select_file)
process_button.pack(pady=5)

# --- Status Label ---
status_label = tk.Label(root, text="", fg="blue")
status_label.pack(pady=5)

# --- Run the GUI event loop ---
root.mainloop()
