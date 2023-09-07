## Pull Request (PR) Checklist
If you'd like to contribute, please follow the checklist below when submitting a PR. This will help us review and merge your changes faster! Thank you for contributing!

1. **Type of PR**: Indicate the type of PR by adding a label in square brackets at the beginning of the title, such as `[Bugfix]`, `[Feature]`, `[Enhancement]`, `[Refactor]`, or `[Documentation]`.

2. **Short Description**: Provide a brief, informative description of the PR that explains the changes made.

3. **Issue(s) Linked**: Mention any related issue(s) by using the keyword `Fixes` or `Closes` followed by the respective issue number(s) (e.g., Fixes #123, Closes #456).

4. **Branch**: Ensure that you have created a new branch for the changes, and it is based on the latest version of the `main` branch.

5. **Code Changes**: Make sure the code changes are minimal, focused, and relevant to the issue or feature being addressed.

6. **Commit Messages**: Write clear and concise commit messages that explain the purpose of each commit.

7. **Tests**: Include unit tests and/or integration tests for any new code or changes to existing code. Make sure all tests pass before submitting the PR.

8. **Documentation**: Update relevant documentation (e.g., README, inline comments, or external documentation) to reflect any changes made.

9. **Review Requested**: Request a review from at least one other contributor or maintainer of the repository.

10. **Video Submission** (For Complex/Large PRs): If your PR introduces significant changes, complexities, or a large number of lines of code, submit a brief video walkthrough along with the PR. The video should explain the purpose of the changes, the logic behind them, and how they address the issue or add the proposed feature. This will help reviewers to better understand your contribution and expedite the review process.

## Pull Request Naming Convention

Use the following naming convention for your PR branches:

```
<type>/<short-description>-<issue-number>
```

- `<type>`: The type of PR, such as `bugfix`, `feature`, `enhancement`, `refactor`, or `docs`. Multiple types are ok and should appear as <type>, <type2>
- `<short-description>`: A brief description of the changes made, using hyphens to separate words.
- `<issue-number>`: The issue number associated with the changes made (if applicable).

Example:

```
feature/advanced-chunking-strategy-123
```