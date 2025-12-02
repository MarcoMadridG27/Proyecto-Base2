import pandas as pd
import os
import glob

def main():
    source_file = "songs/songs_with_attributes_and_lyrics.csv"
    output_dir = "songs/subsets"
    
    if not os.path.exists(source_file):
        print(f"Source file not found: {source_file}")
        # Try to find it in current dir or parent
        if os.path.exists("songs_with_attributes_and_lyrics.csv"):
            source_file = "songs_with_attributes_and_lyrics.csv"
        else:
            print("Skipping extraction.")
            return

    os.makedirs(output_dir, exist_ok=True)
    
    print(f"Loading {source_file}...")
    try:
        df = pd.read_csv(source_file, on_bad_lines='skip', quoting=1) # QUOTE_ALL=1
    except Exception as e:
        print(f"Error loading CSV: {e}")
        return

    print(f"Total rows: {len(df)}")
    
    # Deduplicate
    if 'id' in df.columns:
        df = df.drop_duplicates(subset=['id'])
    elif 'name' in df.columns and 'artist' in df.columns:
        df = df.drop_duplicates(subset=['name', 'artist'])
    
    print(f"Unique rows: {len(df)}")
    
    sizes = [1000, 2000, 4000, 8000, 16000, 32000, 64000, 128000]
    
    for size in sizes:
        if size > len(df):
            break
            
        subset = df.head(size)
        filename = f"songs_{size//1000}k.csv"
        filepath = os.path.join(output_dir, filename)
        
        subset.to_csv(filepath, index=False, quoting=1)
        print(f"Created {filepath} with {len(subset)} rows")

if __name__ == "__main__":
    main()
