# Contribution Guide

Thank you for your interest in contributing to this repository! To ensure a smooth and productive collaboration, please follow the workflow and guidelines outlined below.

## Contribution Workflow

### 1. Create a Development Branch
- Start by creating a branch prefixed with `dev-` from the `main` branch.
- This branch is yours to use as needed. It can be dirty or maintained in any way that suits your development process.

### 2. Create a Pull Request
- Once your changes are ready for feedback, format your code with `format.sh` and create a Pull Request (PR) from your `dev-` branch.
- The purpose of this PR is to gather feedback and comments from reviewers before finalizing the changes.
- Address all comments and make necessary fixes directly on the `dev-` branch until the PR is approved.

### 3. Squash Commits and Finalize
- Once the reviewer approves, close the PR with the Squash and Merge option.
- Write a clean and detailed commit message summarizing the changes.
- Complete the merge by deleting the `dev-` branch.

## Example Commit Message

**Commit Summary:**
```
Summary: Implement VCD parser module and update documentation

This commit introduces the VCD parser module capable of parsing design hierarchies, extracting module declarations and entity initializations, and generating structured JSON outputs. It also includes:
- Updates to `.gitignore` to exclude JSON source files.
- Comprehensive documentation detailing module usage, workflow, and output structure.
```

## Productivity Trick
To craft a clean and comprehensive commit message, you can feed all the diffs and previous commit messages into a tool like GPT and ask it to generate a well-structured commit message. Here's an example prompt:

```
Using the following diffs and commit messages:
<insert diffs>
<insert previous commit messages>

Generate a clean, detailed commit message for a squash commit.
```

By leveraging this approach, you can save time and ensure consistency in your commit messages.

---

For any questions or further clarifications, please open an issue in the repo with the question. Happy coding!

