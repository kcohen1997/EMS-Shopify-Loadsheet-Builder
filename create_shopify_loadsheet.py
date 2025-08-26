import pandas as pd
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import chardet
import threading
import os
import re
from html import unescape

# --- Global variable to hold processed DataFrame ---
processed_df = None

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

# --- Clean Description (strip HTML + special characters) ---
def clean_description(text):
    if pd.isna(text):
        return "#N/A"
    text = str(text)
    text = unescape(text)  # convert HTML entities (&amp; -> &)
    text = re.sub(r"<[^>]*>", " ", text)  # remove HTML tags

    # allow letters, numbers, spaces, common punctuation & symbols
    text = re.sub(r"[^a-zA-Z0-9\s.,;:!?(){}\[\]\-_'\"&/%+°•$@]", "", text)

    # normalize whitespace
    text = re.sub(r"\s+", " ", text).strip()

    return text if text else "#N/A"

def _process_file_worker(file_path):
    global processed_df

    try:
        required_columns = ['Title', 'Variant Price', 'Published', 'Status', 'Handle', 'Variant SKU']

        # Detect encoding
        with open(file_path, 'rb') as f:
            raw_data = f.read()
            encoding = chardet.detect(raw_data)['encoding'] or 'utf-8'

        # Read CSV
        try:
            df = pd.read_csv(file_path, encoding=encoding, low_memory=False)
        except pd.errors.ParserError as e:
            raise ValueError("The selected file could not be parsed as a valid CSV. Please check the format.") from e
        except Exception as e:
            raise ValueError("An unexpected error occurred while reading the file.") from e

        # Check for required columns
        missing = [col for col in required_columns if col not in df.columns]
        if missing:
            raise ValueError(f"The following required columns are missing in the CSV file: {', '.join(missing)}")

        df['Variant Price'] = pd.to_numeric(df['Variant Price'], errors='coerce')

        df['Title'] = df['Title'].ffill().infer_objects(copy=False)
        df['Published'] = df['Published'].infer_objects().ffill().infer_objects(copy=False)
        df['Status'] = df['Status'].ffill().infer_objects(copy=False)

        columns_to_ffill = [
            'Fitment (product.metafields.convermax.fitment)',
            'Type',
            'Length (product.metafields.custom.length)',
            'Width (product.metafields.custom.width)',
            'Height (product.metafields.custom.height)'
        ]

        for col in columns_to_ffill:
            if col in df.columns and 'Handle' in df.columns:
                df[col] = df.groupby('Handle')[col].ffill().infer_objects(copy=False)

        # Filter valid entries
        df = df[
            (df['Variant Price'] > 0) &
            (df['Published'].astype(str).str.lower() == 'true') &
            (df['Status'].astype(str).str.lower() == 'active')
        ]

        df['Full Title'] = df.apply(build_full_title, axis=1)
        df['Variant Price'] = df['Variant Price'].map(lambda x: f"${x:,.2f}" if pd.notnull(x) else "")

        if 'Variant Grams' in df.columns:
            df['Weight (lb)'] = round(df['Variant Grams'] * 0.00220462, 2)
        else:
            df['Weight (lb)'] = "#N/A"

        if 'Fitment (product.metafields.convermax.fitment)' in df.columns:
            df['Fitment (product.metafields.convermax.fitment)'] = (
                df['Fitment (product.metafields.convermax.fitment)']
                .fillna('#N/A')
                .astype(str)
                .str.replace('|', ' ', regex=False)
                .str.replace('\n', ', ', regex=False)
            )

        for dim_col in ['Length (product.metafields.custom.length)', 'Width (product.metafields.custom.width)', 'Height (product.metafields.custom.height)']:
            if dim_col in df.columns:
                df[dim_col] = df[dim_col].fillna('#N/A').astype(str).str.replace("'", '', regex=False)

        df['Product Link'] = 'https://eddiemotorsports.com/products/' + df['Handle'].astype(str)

        # Handle image column
        df.rename(columns={'Variant Image': 'Image Link'}, inplace=True)
        df['Image Link'] = df['Image Link'].fillna('#N/A').astype(str)

        final_variant_list = df.copy()
        final_column_list = [
            'Variant SKU', 'Full Title', 'Type', 'Handle', 'Title', 'Variant Price',
            'Length (product.metafields.custom.length)', 'Width (product.metafields.custom.width)', 'Height (product.metafields.custom.height)',
            'Weight (lb)', 'Fitment (product.metafields.convermax.fitment)', 'Body (HTML)',
            'Image Link', 'Product Link'
        ]

        for col in final_column_list:
            if col not in final_variant_list.columns:
                final_variant_list[col] = '#N/A'

        final_variant_list = final_variant_list[final_column_list]
        final_variant_list.rename(columns={
            'Variant SKU': 'Part #',
            'Type': 'Category',
            'Variant Price': 'Retail Price',
            'Length (product.metafields.custom.length)': 'Length (in)',
            'Width (product.metafields.custom.width)': 'Width (in)',
            'Height (product.metafields.custom.height)': 'Height (in)',
            'Fitment (product.metafields.convermax.fitment)': 'Fitment',
            'Body (HTML)': 'Description'
        }, inplace=True)

        # Clean Description text
        if 'Description' in final_variant_list.columns:
            final_variant_list['Description'] = final_variant_list['Description'].apply(clean_description)

        final_variant_list.fillna("#N/A", inplace=True)
        processed_df = final_variant_list

        # UI updates (main thread only)
        root.after(0, lambda: [
            progress.stop(),
            progress.pack_forget(),
            status_label.config(text="Processing complete."),
            save_button.config(state=tk.NORMAL),
            process_button.config(state=tk.NORMAL),
            root.after(100, lambda: messagebox.showinfo("Success", "File processed. You can now save the output."))
        ])

    except Exception as e:
        import traceback
        traceback.print_exc()
        root.after(0, lambda: [
            progress.stop(),
            progress.pack_forget(),
            status_label.config(text="An error occurred during processing."),
            process_button.config(state=tk.NORMAL),
            messagebox.showerror("Processing Error", str(e))
        ])

def truncate_text(text, max_len=50):
    return text if len(text) <= max_len else f"...{text[-(max_len - 3):]}"

def process_file():
    file_path = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv")])
    if not file_path:
        return

    if not file_path.lower().endswith('.csv'):
        messagebox.showwarning("Invalid File", "Please select a CSV file.")
        return

    file_name = os.path.basename(file_path)
    display_name = truncate_text(file_name)
    file_name_label.config(text=f"Selected File: {display_name}")

    def on_enter(event):
        file_name_label.config(text=f"Selected File: {file_name}")

    def on_leave(event):
        file_name_label.config(text=f"Selected File: {display_name}")

    file_name_label.bind("<Enter>", on_enter)
    file_name_label.bind("<Leave>", on_leave)

    status_label.config(text="Processing...")
    save_button.config(state=tk.DISABLED)
    process_button.config(state=tk.DISABLED)
    progress.pack(pady=5)
    progress.start()

    # Start background processing
    threading.Thread(target=_process_file_worker, args=(file_path,), daemon=True).start()

def save_file():
    global processed_df
    if processed_df is None:
        messagebox.showwarning("No Data", "You must process a file before saving.")
        return

    output_file_path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv")])
    if output_file_path:
        processed_df.to_csv(output_file_path, index=False)
        status_label.config(text="File saved successfully.")
        messagebox.showinfo("Saved", f"File saved to:\n{output_file_path}")
    else:
        status_label.config(text="Save cancelled.")

# --- GUI setup ---
root = tk.Tk()
root.title("EMS Loadsheet Builder")
root.geometry("420x200")

process_button = tk.Button(root, text="1. Select & Process CSV File", command=process_file)
process_button.pack(pady=(20, 5))

file_name_label = tk.Label(root, text="", fg="gray", anchor='w', justify='left')
file_name_label.pack()

save_button = tk.Button(root, text="2. Save Processed File", command=save_file, state=tk.DISABLED)
save_button.pack(pady=(10, 5))

progress = ttk.Progressbar(root, mode='indeterminate')
status_label = tk.Label(root, text="", fg="blue")
status_label.pack(pady=5)

root.mainloop()
