# Moderation Interface - Visual Guide

## Overview
This document provides a visual description of the Django Admin moderation interface.

## Login Screen
When accessing `/admin/`, users see the standard Django admin login:
```
┌──────────────────────────────────────┐
│   Django Administration             │
├──────────────────────────────────────┤
│                                      │
│   Username: ___________________      │
│   Password: ___________________      │
│                                      │
│   [ Log in ]                         │
│                                      │
└──────────────────────────────────────┘
```

## Admin Homepage
After login, staff users see available sections:
```
┌────────────────────────────────────────────────────┐
│ Django administration                              │
│ Welcome, admin@example.com                 [Logout]│
├────────────────────────────────────────────────────┤
│                                                    │
│ Site administration                                │
│                                                    │
│ 📱 SOCIAL MEDIA                                    │
│   ├─ Inappropriate content reports (+Add | View)  │
│   ├─ Media posts                  (+Add | View)   │
│   ├─ Text comments                (+Add | View)   │
│   └─ Media                        (+Add | View)   │
│                                                    │
│ 👥 USERS                                           │
│   ├─ Users                        (+Add | View)   │
│   └─ Banned emails               (+Add | View)    │
│                                                    │
│ 🦁 SPECIES                                         │
│   └─ Species names               (+Add | View)    │
│                                                    │
└────────────────────────────────────────────────────┘
```

## Moderation Queue - List View
The main moderation interface (`/admin/socialmedia/inappropriatecontentreport/`):

```
┌────────────────────────────────────────────────────────────────────────────────┐
│ Django administration > Social media > Inappropriate content reports           │
├────────────────────────────────────────────────────────────────────────────────┤
│                                                                                │
│ Inappropriate content reports                                 [+ Add report]  │
│                                                                                │
│ ┌─────────────┐                                                               │
│ │ Action: ▼   │  [Go]        Search: [_______________] 🔍                     │
│ │ ----------  │                                                               │
│ │ ✅ Mark as  │              Filters:                                         │
│ │    resolved │              ┌──────────────────┐                            │
│ │ ⚠️  Issue   │              │ Resolved         │                            │
│ │    warning  │              │ ☑ Pending (12)   │                            │
│ │ 🚫 Ban user │              │ ☐ Resolved (45)  │                            │
│ └─────────────┘              │                  │                            │
│                              │ By date          │                            │
│ ☐ Select all 12 reports      │ ☐ Today (3)      │                            │
│                              │ ☐ Past 7 days    │                            │
├──┬────┬────────┬──────────────┬─────────────┬──────────┬──────┬──────────────┤
│☐│ID  │Content │Preview       │Reported User│Reporter  │Warn  │Created       │
│  │    │Type    │              │             │          │      │              │
├──┼────┼────────┼──────────────┼─────────────┼──────────┼──────┼──────────────┤
│☐│3f7a│📝 Post │Spam content  │John Doe     │Jane Smith│⚠️ 2  │2024-02-15    │
│  │    │        │selling...    │(john@ex.com)│          │      │10:30 AM      │
├──┼────┼────────┼──────────────┼─────────────┼──────────┼──────┼──────────────┤
│☐│9b2c│💬 Cmnt │Rude language │Bob Smith    │Alice Lee │⚠️ 0  │2024-02-15    │
│  │    │        │towards...    │(bob@ex.com) │          │      │09:15 AM      │
├──┼────┼────────┼──────────────┼─────────────┼──────────┼──────┼──────────────┤
│☐│1e4d│📝 Post │Inappropriate │Mike Johnson │Tom Brown │⚠️ 3  │2024-02-14    │
│  │    │        │wildlife...   │(mike@ex.com)│          │      │04:22 PM      │
└──┴────┴────────┴──────────────┴─────────────┴──────────┴──────┴──────────────┘
│                                                                                │
│ Showing 1-12 of 12 reports                                [< Prev | Next >]   │
│                                                                                │
└────────────────────────────────────────────────────────────────────────────────┘
```

## Report Detail View
When clicking on a report ID:

```
┌────────────────────────────────────────────────────────────────────────────────┐
│ Change inappropriate content report                                            │
├────────────────────────────────────────────────────────────────────────────────┤
│                                                                                │
│ ┌─ REPORT INFORMATION ────────────────────────────────────────────────────────┐│
│ │                                                                              ││
│ │ ID:       3f7a912b-4c2e-4d3a-b8f1-9e6c3a7b1d2f                              ││
│ │ Resolved: ☐ (Unchecked = Pending)                                           ││
│ │ Created:  February 15, 2024, 10:30 a.m.                                     ││
│ │ Modified: February 15, 2024, 10:30 a.m.                                     ││
│ │                                                                              ││
│ └──────────────────────────────────────────────────────────────────────────────┘│
│                                                                                │
│ ┌─ REPORTED CONTENT ──────────────────────────────────────────────────────────┐│
│ │                                                                              ││
│ │ ┌────────────────────────────────────────────────────────────────────────┐  ││
│ │ │ Post: Selling wildlife products                                        │  ││
│ │ │                                                                        │  ││
│ │ │ Text: Check out these amazing wildlife products for sale! Get 50%     │  ││
│ │ │       off with code WILD50. Link: spam-site.com                       │  ││
│ │ │                                                                        │  ││
│ │ │ Species: Not specified                                                │  ││
│ │ │ Location: Los Angeles, CA                                             │  ││
│ │ │ Encounter Date: February 10, 2024, 2:15 p.m.                          │  ││
│ │ │ Privacy: Public                                                       │  ││
│ │ │ Created: February 10, 2024, 2:30 p.m.                                 │  ││
│ │ └────────────────────────────────────────────────────────────────────────┘  ││
│ │                                                                              ││
│ │ Reported comment: None                                                       ││
│ │ Reported post:    MediaPost object (3f7a912b)                               ││
│ │                                                                              ││
│ └──────────────────────────────────────────────────────────────────────────────┘│
│                                                                                │
│ ┌─ USERS INVOLVED ────────────────────────────────────────────────────────────┐│
│ │                                                                              ││
│ │ Reported by:   Jane Smith (jane.smith@example.com) [View profile]           ││
│ │ Reported user: John Doe (john.doe@example.com) [View profile]               ││
│ │                                                                              ││
│ │ ┌────────────────────────────────────────────────────────────────────────┐  ││
│ │ │ Moderation History for John Doe                                        │  ││
│ │ │                                                                        │  ││
│ │ │ Total Reports:    5                                                   │  ││
│ │ │ Pending Reports:  2                                                   │  ││
│ │ │ Resolved Reports: 3                                                   │  ││
│ │ │ Total Warnings:   2                                                   │  ││
│ │ │                                                                        │  ││
│ │ │ Previous Warning Notes:                                               │  ││
│ │ │ • 2024-02-10: Posting spam links to commercial websites               │  ││
│ │ │ • 2024-01-15: Off-topic content not related to wildlife               │  ││
│ │ └────────────────────────────────────────────────────────────────────────┘  ││
│ │                                                                              ││
│ └──────────────────────────────────────────────────────────────────────────────┘│
│                                                                                │
│ ┌─ MODERATION ACTIONS ────────────────────────────────────────────────────────┐│
│ │                                                                              ││
│ │ Add notes when taking moderation actions                                     ││
│ │                                                                              ││
│ │ Warning notes:                                                               ││
│ │ ┌──────────────────────────────────────────────────────────────────────┐    ││
│ │ │ ____________________________________________________________          │    ││
│ │ │ ____________________________________________________________          │    ││
│ │ │ ____________________________________________________________          │    ││
│ │ └──────────────────────────────────────────────────────────────────────┘    ││
│ │                                                                              ││
│ └──────────────────────────────────────────────────────────────────────────────┘│
│                                                                                │
│ [Save and continue editing]  [Save and add another]  [Save]                   │
│                                                                                │
│ [Delete]                                                (Superuser only)       │
│                                                                                │
└────────────────────────────────────────────────────────────────────────────────┘
```

## Bulk Action Flow
When moderator selects multiple reports and chooses an action:

```
┌────────────────────────────────────────────────────────────────────────────────┐
│ Are you sure?                                                                  │
├────────────────────────────────────────────────────────────────────────────────┤
│                                                                                │
│ Are you sure you want to issue warning and delete content for these reports?  │
│                                                                                │
│ This will:                                                                     │
│ • Delete the reported content permanently                                      │
│ • Increment warning count for each user                                        │
│ • Mark reports as resolved                                                     │
│                                                                                │
│ Reports to be processed: 3                                                     │
│                                                                                │
│ ☑ Yes, I'm sure                                                                │
│                                                                                │
│ [Go back]  [Yes, I'm sure]                                                     │
│                                                                                │
└────────────────────────────────────────────────────────────────────────────────┘
```

## Success Message
After completing an action:

```
┌────────────────────────────────────────────────────────────────────────────────┐
│ ✅ Successfully processed 3 report(s): content deleted and warnings issued.    │
└────────────────────────────────────────────────────────────────────────────────┘
```

## Key Visual Elements

### Status Icons
- 📝 Post
- 💬 Comment
- ❓ Unknown content

### Warning Colors
- 🟢 0 warnings (green)
- 🟠 1-2 warnings (orange)
- 🔴 3+ warnings (red)

### Action Buttons
- ✅ Clear report (green)
- ⚠️ Issue warning (yellow/orange)
- 🚫 Ban user (red)

## User Experience Flow

### Typical Moderator Workflow:

1. **Log in** to `/admin/` with staff credentials
2. **Navigate** to Inappropriate content reports
3. **Filter** for "Pending" reports
4. **Review** first report by clicking ID
5. **Assess** content, user history, and warning count
6. **Add notes** explaining decision
7. **Take action**:
   - Save changes only (to add notes without action)
   - Or go back to list and use bulk actions
8. **Bulk action** if multiple similar reports
9. **Verify** success message
10. **Continue** with next report

## Mobile Responsiveness
Django Admin is responsive and works on tablets/mobile devices:
- Tables scroll horizontally
- Forms stack vertically
- Touch-friendly controls
- Filter sidebar collapses

## Accessibility Features
- Keyboard navigation support
- Screen reader compatible
- High contrast mode available
- Focus indicators on all interactive elements
- Descriptive labels and help text

## Performance Features
- Pagination (default 100 items per page)
- Optimized database queries with select_related
- Cached user counts
- Efficient search indexing
- Lazy loading of related objects

## Security Features
- CSRF protection on all forms
- Permission checks on all actions
- Audit trail of all changes
- Read-only fields for data integrity
- Superuser-only deletion rights
- Session timeout protection
