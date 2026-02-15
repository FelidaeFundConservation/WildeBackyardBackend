# Moderation Interface Documentation

## Overview

The Wilde Backyard Backend now includes a comprehensive moderation interface built using Django Admin. This interface allows staff members to review and manage inappropriate content reports efficiently.

## Accessing the Moderation Interface

### Prerequisites
- You must be logged in as a **staff user** (is_staff=True)
- For certain actions (like deleting reports), you need **superuser** privileges

### Access URL
Navigate to: `https://your-domain.com/admin/socialmedia/inappropriatecontentreport/`

Or access through the main admin interface:
1. Go to `https://your-domain.com/admin/`
2. Click on "Social media" section
3. Click on "Inappropriate content reports"

## Features

### List View

The moderation queue displays all reports with the following information:

- **Content Type**: Icon indicating whether it's a Post (📝) or Comment (💬)
- **Content Preview**: First 100 characters of the reported content
- **Reported User**: Link to the user's admin profile
- **Reported By**: Link to the reporter's admin profile
- **Resolved Status**: Whether the report has been handled
- **User Warnings**: Current warning count for the reported user (color-coded)
- **Created Date**: When the report was created

### Filtering Options

Use the right sidebar to filter reports by:
- **Resolved status**: Show only pending or resolved reports
- **Created date**: Filter by date range
- **Modified date**: Filter by last modification date

### Search Functionality

Search for reports using:
- Reported user's email or name
- Reporter's email or name
- Warning notes text

### Sorting

By default, reports are ordered:
1. Unresolved reports first
2. Most recent reports first

Click on column headers to sort by other fields.

## Moderation Actions

### 1. View Report Details

Click on any report ID to view full details including:

- **Report Information**: ID, status, timestamps
- **Content Details**: Full content with formatting, including:
  - For posts: Title, text, species, location, media files
  - For comments: Full text, upvote count
- **User Information**: 
  - Links to both reported user and reporter profiles
  - User moderation history
  - Total warnings and previous reports
- **Previous Warning Notes**: History of warnings issued to this user

### 2. Mark as Resolved (No Action)

**When to use**: Content doesn't violate policies; report is unfounded

**How to use**:
1. Select one or more reports using checkboxes
2. Choose "✅ Mark as resolved (no action needed)" from the Actions dropdown
3. Click "Go"

**Effect**: 
- Report marked as resolved
- No action taken against user or content
- Content remains visible

### 3. Issue Warning and Delete Content

**When to use**: Minor policy violations (e.g., rudeness, off-topic content)

**How to use**:
1. (Optional) Open the report and add warning notes explaining the violation
2. Select one or more reports using checkboxes
3. Choose "⚠️ Issue warning and delete content" from the Actions dropdown
4. Click "Go"

**Effect**:
- Reported content is permanently deleted
- User's warning count incremented by 1
- Report marked as resolved
- Warning notes saved (or default message added)
- User can continue using the platform

**Note**: Consider banning after 3+ warnings

### 4. Ban User and Delete All Content

**When to use**: Severe violations (explicit content, harassment, spam) or repeat offenders

**How to use**:
1. (Optional) Open the report and add ban reason in warning notes
2. Select one or more reports using checkboxes
3. Choose "🚫 BAN user and delete ALL their content" from the Actions dropdown
4. Click "Go"
5. Confirm the action (this is irreversible!)

**Effect**:
- **ALL** posts and comments by the user are permanently deleted
- User's email added to banned list
- User cannot create new accounts with same email
- All pending reports for this user are resolved
- Ban reason saved in database

**Warning**: This action is permanent and affects ALL user content, not just reported items.

## Best Practices

### Review Process

1. **Review the Content**: Click on the report to see full details
2. **Check User History**: Review the user's moderation history section
3. **Consider Context**: Look at the user's warning count and previous violations
4. **Make Decision**:
   - First offense + minor violation → Warning
   - Multiple warnings → Ban
   - Severe violation → Immediate ban
5. **Document**: Add clear notes explaining your decision

### Escalation Guidelines

- **0 warnings**: Consider warning for first offense
- **1-2 warnings**: Issue another warning or consider short-term action
- **3+ warnings**: Strong candidate for permanent ban
- **Severe violation**: Immediate ban regardless of history

### Notes Best Practices

Always add specific warning notes:
- ❌ Bad: "Inappropriate content"
- ✅ Good: "Posted spam links advertising commercial products in wildlife observation post"

Clear notes help:
- Other moderators understand decisions
- Provide context if user appeals
- Document patterns of behavior

## Common Workflows

### Handling a Single Report

1. Open the moderation queue
2. Click on the first unresolved report
3. Review content and user history
4. Add appropriate warning notes
5. Save and use the action buttons, or use bulk actions from list view

### Bulk Processing

1. Filter for unresolved reports
2. Review each report quickly
3. Select all reports with same decision (e.g., all false reports)
4. Apply bulk action
5. Repeat for other categories

### Investigating a User

1. Click on the reported user's name to open their profile
2. Review their warnings count
3. Check their post/comment history
4. Return to moderation queue
5. Use "User email" search to find all reports for this user
6. Make comprehensive decision

## Technical Details

### Permissions

- **Staff users (is_staff=True)**: Can view and moderate all reports
- **Superusers (is_superuser=True)**: Additionally can delete report records

### Data Integrity

- Reports are never automatically deleted (audit trail)
- Only superusers can delete reports (for data integrity)
- Deleted content sets foreign keys to NULL (preserves report record)
- Banned emails are stored separately (prevents ban circumvention)

### Performance

- Admin interface uses optimized queries with select_related/prefetch_related
- Large datasets are paginated automatically
- Search is indexed on frequently-queried fields

## Troubleshooting

### "No reports to display"
- All reports are resolved! Check the "resolved" filter
- Try clearing all filters to see full dataset

### Can't see moderation actions
- Verify you're logged in as staff user
- Ensure you have is_staff=True permission
- Check that you're on the list view (not detail view) for bulk actions

### Action didn't work
- Check Django messages at top of page for error details
- Verify report wasn't already resolved
- Ensure content still exists (may have been deleted by another moderator)

## API Integration

The moderation interface complements existing API endpoints:

- `POST /v1/socialmedia/api/posts/reports/create` - Users create reports
- `GET /v1/socialmedia/api/posts/reports/review` - API for getting next report
- `POST /v1/socialmedia/api/posts/reports/clear` - API to clear report
- `POST /v1/socialmedia/api/posts/reports/warn` - API to issue warning
- `POST /v1/socialmedia/api/posts/reports/ban` - API to ban user

The Django Admin interface provides a more comprehensive and user-friendly alternative to these API endpoints while using the same underlying models and business logic.

## Future Enhancements

Potential improvements to consider:

- Email notifications to users when warned/banned
- Appeal process for banned users
- Automated flagging based on keywords
- Moderation analytics dashboard
- Custom moderation workflows per content type
- Integration with external moderation services
