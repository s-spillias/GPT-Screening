
import csv
import glob

def count_unique_values(pattern, directory):
    # Get a list of files matching the pattern in the directory
    file_list = glob.glob(directory + '/' + pattern)

    # Initialize a dictionary to store counts of unique values for each position
    counts = {}

    # Iterate over the files
    max_rows = 0
    for file in file_list:
        with open(file, 'r') as csv_file:
            csv_reader = csv.reader(csv_file)
            df = pd.DataFrame(csv_reader) # Assuming the first row contains the header

            # Update the maximum number of rows if necessary
            num_rows = sum(1 for row in csv_reader)
            max_rows = max(max_rows, num_rows)

            # Iterate over each position in the header
            for position in header:
                counts.setdefault(position, set())  # Initialize an empty set for each position

            # Rewind the file to read the rows again
            csv_file.seek(0)
            next(csv_reader)  # Skip the header

            # Iterate over each row in the CSV file
            for row in csv_reader:
                # Iterate over each position in the row
                for i, value in enumerate(row):
                    position = header[i]
                    counts[position].add(value)  # Add the value to the set for the corresponding position

    # Create a 2D array to store the counts of unique values
    positions = sorted(counts.keys())
    unique_counts = [[len(counts[position])] * max_rows for position in positions]

    # Save the output as a CSV file
    with open('output.csv', 'w', newline='') as output_file:
        csv_writer = csv.writer(output_file)
        csv_writer.writerow(['Position'] + list(range(max_rows)))
        for position, counts in zip(positions, unique_counts):
            csv_writer.writerow([position] + counts)

    return unique_counts

# Specify the pattern and directory
pattern = '*rand*'  # Replace with your desired pattern
directory = './Paper-Results/rand_test'  # Replace with the directory path you want to search

# Call the function to count unique values and save the output
unique_counts = count_unique_values(pattern, directory)

# Print the counts of unique values for each position
for position, counts in zip(sorted(counts.keys()), unique_counts):
    print(f"Position '{position}': {counts} unique value(s)")

print("Output saved as 'output.csv'.")
