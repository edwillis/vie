import os
# open .copilot_instructions.txt from the current directory
# add each line to a buffer in memory

buffer = []
with open('script/.copilot-instructions.txt', 'r') as file:
	buffer = file.readlines()

# Add "Automatically generated context follows:" to the buffer

buffer.append("Automatically generated context follows:\n")

# Add "Project Directory Structure:" to the buffer

buffer.append("Project Directory Structure:\n")

# walk the vie directory, excluding the build directory, the .venv one, and all __pycache__ 
# directories and emit the paths, relative to the top level "vie" directory, to stdout
def compute_project_structure(line_buffer, root="."):
	for dirpath, dirnames, filenames in os.walk(root):
		# Exclude build, .venv, and __pycache__ directories
		dirnames[:] = [d for d in dirnames if d not in [".vscode", ".pytest_cache", 'build', '.venv', '__pycache__']]
		for filename in filenames:
			# append the path but add a newline at the end
			line_buffer.append(os.path.relpath(os.path.join(dirpath, filename), root) + '\n')

compute_project_structure(buffer)
with open('.copilot-instructions.txt', 'w') as file1:
    file1.writelines(buffer)
	
with open('.copilot-test-instructions.txt', 'w') as file2:
    file2.writelines(buffer)