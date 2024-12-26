import os
import re

REGEX_STRING_MATCH_ENV_VAR = r"\$\{(\w+)\}"


class FlistFormatter:
    def __init__(self):
        """Initializes an empty class FlistFormatter instance."""

    def __replace_env_var(self, match):
        """Private method for replacing placeholders with enviroment variables."""

        env_var = match.group(1)
        env_value = os.environ.get(env_var)
        if env_value is None:
            raise ValueError(f"Error: Environment variable '{env_var}' is not set.")
        return env_value

    def format_cva6(self, flist_path):
        """Public method for formating file list to plain text with absolute file path."""

        env_var_pattern = re.compile(REGEX_STRING_MATCH_ENV_VAR)
        formatted_lines = []

        with open(flist_path, "r") as flist_file:
            for line in flist_file:
                stripped_line = line.strip()
                if not stripped_line or stripped_line.startswith("//") or stripped_line.startswith("#"):
                    continue

                replaced_line = env_var_pattern.sub(self.__replace_env_var, stripped_line)

                if replaced_line.startswith("+incdir+"):
                    include_path = replaced_line[8:]
                    if os.path.isdir(include_path):
                        for root, _, files in os.walk(include_path):
                            for file in files:
                                file_path = os.path.join(root, file)
                                formatted_lines.append(file_path)
                    else:
                        raise FileNotFoundError(f"Directory not found: {include_path}")

                elif replaced_line.startswith("-F"):
                    f_file_path = replaced_line[3:].strip()
                    if os.path.isfile(f_file_path):
                        formatted_lines.extend(self.format_cva6(f_file_path).splitlines())
                    else:
                        raise FileNotFoundError(f"File not found: {f_file_path}")
                else:
                    formatted_lines.append(replaced_line)

        return "\n".join(formatted_lines)


if __name__ == "__main__":
    # Example usage
    formatter = FlistFormatter()
