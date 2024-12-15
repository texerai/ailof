# Contribution Guide

Thank you for your interest in contributing to this repository! To ensure a smooth and productive collaboration, please follow the workflow and guidelines outlined below.

## Contribution Workflow

### 1. Create a Development Branch
- Start by creating a branch prefixed with `dev-` from the `main` branch.
- This branch is yours to use as needed. It can be dirty or maintained in any way that suits your development process.

### 2. Create a Feedback Pull Request
- Once your changes are ready for feedback, create a Pull Request (PR) from your `dev-` branch.
- The purpose of this PR is **not for merging** but to gather feedback and comments from reviewers.
- Address all comments and make necessary fixes directly on the `dev-` branch until the PR is approved.
- Once the reviewer approves, close the PR with the comment: `ready to merge`.

### 3. Squash Commits and Finalize
- After the PR is approved, squash all commits on your `dev-` branch into a **single commit** with a clean and detailed message.
- Push the squashed commit and create a final merge PR from your `dev-` branch to the `main` branch.
- Once approved, the merge can be completed.

## How to Squash Commits
To squash commits, follow these steps:

1. **Start an Interactive Rebase**:
   ```bash
   git rebase -i main
   ```
2. **Choose the Squash Option**:
   - In the interactive rebase editor, mark the first commit as `pick` and all subsequent commits as `squash` or `s`.
   - Save and close the editor.

3. **Edit the Commit Message**:
   - Combine the commit messages into a single, detailed message or write a new message summarizing all changes.
   - Save and close the editor to complete the rebase.

4. **Push the Changes**:
   - Force push your branch to update the PR:
     ```bash
     git push --force
     ```

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

