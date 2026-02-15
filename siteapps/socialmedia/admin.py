from django.contrib import admin, messages
from django.db import transaction
from django.urls import reverse
from django.utils.html import escape, format_html
from django.utils.safestring import mark_safe

from siteapps.users.models import BannedEmail

from .models import InappropriateContentReport, Media, MediaPost, TextComment


@admin.register(InappropriateContentReport)
class InappropriateContentReportAdmin(admin.ModelAdmin):
    """
    Django Admin interface for managing content moderation reports.
    Provides a comprehensive view of reports with custom actions for moderation workflow.
    """

    # Constants for content truncation and limits
    TITLE_PREVIEW_LENGTH = 50
    TEXT_PREVIEW_LENGTH = 100
    MAX_BAN_REASON_LENGTH = 800

    # Display columns in list view
    list_display = (
        "id",
        "get_content_type",
        "get_content_preview",
        "reported_user_link",
        "reported_by_link",
        "resolved",
        "get_user_warnings",
        "created",
    )

    # Filters in the right sidebar
    list_filter = (
        "resolved",
        "created",
        "modified",
    )

    # Search fields
    search_fields = (
        "reported_user__email",
        "reported_user__name",
        "reported_by__email",
        "reported_by__name",
        "warning_notes",
    )

    # Read-only fields
    readonly_fields = (
        "id",
        "created",
        "modified",
        "reported_by",
        "reported_user",
        "reported_comment",
        "reported_post",
        "get_content_detail",
        "get_user_history",
    )

    # Fields to display in detail view
    fieldsets = (
        (
            "Report Information",
            {
                "fields": (
                    "id",
                    "resolved",
                    "created",
                    "modified",
                )
            },
        ),
        (
            "Reported Content",
            {
                "fields": (
                    "get_content_detail",
                    "reported_comment",
                    "reported_post",
                )
            },
        ),
        (
            "Users Involved",
            {
                "fields": (
                    "reported_by",
                    "reported_user",
                    "get_user_history",
                )
            },
        ),
        (
            "Moderation Actions",
            {
                "fields": ("warning_notes",),
                "description": "Add notes when taking moderation actions",
            },
        ),
    )

    # Default ordering - unresolved reports first, then most recent
    ordering = ("resolved", "-created")

    # Custom actions
    actions = [
        "mark_resolved_no_action",
        "issue_warning_and_delete",
        "ban_user_and_delete_all_content",
    ]

    # Custom display methods
    def get_content_type(self, obj):
        """Display the type of content reported"""
        if obj.reported_post:
            return "📝 Post"
        elif obj.reported_comment:
            return "💬 Comment"
        return "❓ Unknown"

    get_content_type.short_description = "Content Type"

    def get_content_preview(self, obj):
        """Display a preview of the reported content"""
        if obj.reported_post:
            title = obj.reported_post.title[:self.TITLE_PREVIEW_LENGTH]
            # Add ellipsis if title was truncated
            if len(obj.reported_post.title) > self.TITLE_PREVIEW_LENGTH:
                title += "..."
            # Escape title once
            escaped_title = escape(title)
            
            text = obj.reported_post.text_content[:self.TEXT_PREVIEW_LENGTH] if obj.reported_post.text_content else ""
            # Add ellipsis if text was truncated
            if text and len(obj.reported_post.text_content) > self.TEXT_PREVIEW_LENGTH:
                text += "..."
            
            return f"{escaped_title} - {escape(text)}" if text else escaped_title
        elif obj.reported_comment:
            text = obj.reported_comment.text_content or ""
            preview = text[:self.TEXT_PREVIEW_LENGTH]
            if len(text) > self.TEXT_PREVIEW_LENGTH:
                preview += "..."
            return escape(preview)
        return "Content deleted"

    get_content_preview.short_description = "Content Preview"

    def get_content_detail(self, obj):
        """Display full content details with formatting"""
        if obj.reported_post:
            post = obj.reported_post
            # Escape all user-generated content
            title = escape(post.title)
            text_content = escape(post.text_content or 'No text content')
            species = escape(str(post.species) if post.species else 'Not specified')
            locality = escape(post.geocoded_location_locality or 'Unknown')
            state = escape(post.geocoded_location_state or '')
            encounter_date = escape(str(post.encounter_datetime))
            privacy = escape(str(post.geoprivacy))
            created = escape(str(post.created))
            
            details = f"""
            <div style="padding: 10px; background: #f5f5f5; border-radius: 5px;">
                <h3>Post: {title}</h3>
                <p><strong>Text:</strong> {text_content}</p>
                <p><strong>Species:</strong> {species}</p>
                <p><strong>Location:</strong> {locality}, {state}</p>
                <p><strong>Encounter Date:</strong> {encounter_date}</p>
                <p><strong>Privacy:</strong> {privacy}</p>
                <p><strong>Created:</strong> {created}</p>
            """
            if post.media:
                media_path = escape(post.media.file_cloud_path)
                details += f'<p><strong>Media:</strong> {media_path}</p>'
            details += "</div>"
            return mark_safe(details)
        elif obj.reported_comment:
            comment = obj.reported_comment
            # Escape all user-generated content
            text_content = escape(comment.text_content or 'No text content')
            upvote_count = comment.upvoted_by.count()
            created = escape(str(comment.created))
            
            details = f"""
            <div style="padding: 10px; background: #f5f5f5; border-radius: 5px;">
                <h3>Comment</h3>
                <p><strong>Text:</strong> {text_content}</p>
                <p><strong>Upvotes:</strong> {upvote_count}</p>
                <p><strong>Created:</strong> {created}</p>
            </div>
            """
            return mark_safe(details)
        return "Content no longer available (may have been deleted)"

    get_content_detail.short_description = "Content Details"

    def reported_user_link(self, obj):
        """Create a clickable link to the reported user's admin page"""
        if obj.reported_user:
            url = reverse("admin:users_user_change", args=[obj.reported_user.pk])
            # Escape user-generated content for defense in depth
            name = escape(obj.reported_user.name or "No name")
            email = escape(obj.reported_user.email)
            return format_html('<a href="{}">{} ({})</a>', url, name, email)
        return "User deleted"

    reported_user_link.short_description = "Reported User"

    def reported_by_link(self, obj):
        """Create a clickable link to the reporter's admin page"""
        if obj.reported_by:
            url = reverse("admin:users_user_change", args=[obj.reported_by.pk])
            # Escape user-generated content for defense in depth
            name = escape(obj.reported_by.name or "No name")
            email = escape(obj.reported_by.email)
            return format_html('<a href="{}">{} ({})</a>', url, name, email)
        return "Reporter deleted"

    reported_by_link.short_description = "Reported By"

    def get_user_warnings(self, obj):
        """Display warning count for reported user"""
        if obj.reported_user:
            warnings = obj.reported_user.warnings
            color = "red" if warnings >= 3 else "orange" if warnings >= 1 else "green"
            return format_html('<span style="color: {}; font-weight: bold;">⚠️ {}</span>', color, warnings)
        return "-"

    get_user_warnings.short_description = "User Warnings"

    def get_user_history(self, obj):
        """Display moderation history for the reported user"""
        if not obj.reported_user:
            return "User no longer exists"

        user = obj.reported_user
        # Count reports against this user
        total_reports = InappropriateContentReport.objects.filter(reported_user=user).count()
        resolved_reports = InappropriateContentReport.objects.filter(reported_user=user, resolved=True).count()
        pending_reports = total_reports - resolved_reports

        # Get previous warnings
        previous_warnings = InappropriateContentReport.objects.filter(
            reported_user=user, resolved=True, warning_notes__isnull=False
        ).exclude(warning_notes="")

        # Escape user-generated content
        user_display = escape(user.name or user.email)
        
        history = f"""
        <div style="padding: 10px; background: #fff3cd; border-radius: 5px;">
            <h4>Moderation History for {user_display}</h4>
            <p><strong>Total Reports:</strong> {total_reports}</p>
            <p><strong>Pending Reports:</strong> {pending_reports}</p>
            <p><strong>Resolved Reports:</strong> {resolved_reports}</p>
            <p><strong>Total Warnings:</strong> {user.warnings}</p>
        """

        if previous_warnings.exists():
            history += "<h5>Previous Warning Notes:</h5><ul>"
            for warning in previous_warnings[:5]:  # Show last 5 warnings
                # Escape warning notes (staff-created but still escape for safety)
                safe_notes = escape(warning.warning_notes)
                date_str = escape(warning.created.strftime('%Y-%m-%d'))
                history += f"<li><em>{date_str}:</em> {safe_notes}</li>"
            history += "</ul>"

        history += "</div>"
        return mark_safe(history)

    get_user_history.short_description = "User Moderation History"

    # Custom admin actions
    @admin.action(description="✅ Mark as resolved (no action needed)")
    def mark_resolved_no_action(self, request, queryset):
        """Clear reports without taking action - content is acceptable"""
        count = queryset.filter(resolved=False).update(resolved=True)
        self.message_user(
            request,
            f"{count} report(s) marked as resolved without action.",
            messages.SUCCESS,
        )

    @admin.action(description="⚠️ Issue warning and delete content")
    def issue_warning_and_delete(self, request, queryset):
        """Issue a warning to the user and delete the reported content"""
        count = 0
        for report in queryset.filter(resolved=False):
            with transaction.atomic():
                user_to_warn = None

                # Delete the offending content
                if report.reported_comment:
                    user_to_warn = report.reported_comment.created_by
                    report.reported_comment.delete()
                    report.reported_comment = None
                elif report.reported_post:
                    user_to_warn = report.reported_post.created_by
                    report.reported_post.delete()
                    report.reported_post = None

                # Increment warning count
                if user_to_warn:
                    user_to_warn.warnings += 1
                    user_to_warn.save()

                # Mark as resolved with default warning note if none provided
                if not report.warning_notes:
                    report.warning_notes = "Content removed for policy violation. Warning issued."
                report.resolved = True
                report.save()
                count += 1

        self.message_user(
            request,
            f"{count} report(s) processed: content deleted and warnings issued.",
            messages.WARNING,
        )

    @admin.action(description="🚫 BAN user and delete ALL their content")
    def ban_user_and_delete_all_content(self, request, queryset):
        """
        Permanently ban user and remove all their content.
        Use for severe violations or repeated offenses.
        """
        count = 0
        banned_users = []

        for report in queryset.filter(resolved=False):
            with transaction.atomic():
                user_to_ban = None

                # Identify user to ban
                if report.reported_comment and report.reported_comment.created_by:
                    user_to_ban = report.reported_comment.created_by
                elif report.reported_post and report.reported_post.created_by:
                    user_to_ban = report.reported_post.created_by

                if user_to_ban and user_to_ban.email not in banned_users:
                    # Delete ALL content by this user
                    MediaPost.objects.filter(created_by=user_to_ban).delete()
                    TextComment.objects.filter(created_by=user_to_ban).delete()

                    # Add to banned email list
                    # Sanitize ban_reason to prevent any potential issues with special characters
                    ban_reason = (report.warning_notes or "Multiple policy violations - permanent ban")[:self.MAX_BAN_REASON_LENGTH]
                    BannedEmail.objects.get_or_create(email=user_to_ban.email, defaults={"ban_reason": ban_reason})

                    banned_users.append(user_to_ban.email)

                # Clear references and mark resolved
                report.reported_comment = None
                report.reported_post = None
                report.resolved = True
                if not report.warning_notes:
                    # Ensure prefix + reason fits within MAX_BAN_REASON_LENGTH
                    prefix = "User permanently banned: "
                    max_reason_length = self.MAX_BAN_REASON_LENGTH - len(prefix)
                    truncated_reason = ban_reason[:max_reason_length] if len(ban_reason) > max_reason_length else ban_reason
                    report.warning_notes = f"{prefix}{truncated_reason}"
                report.save()
                count += 1

        self.message_user(
            request,
            f"{count} report(s) processed: {len(banned_users)} user(s) permanently banned and all content removed.",
            messages.ERROR,
        )

    def has_delete_permission(self, request, obj=None):
        """Only superusers can delete reports (for data integrity)"""
        return request.user.is_superuser


@admin.register(MediaPost)
class MediaPostAdmin(admin.ModelAdmin):
    """Admin interface for MediaPost model"""

    list_display = (
        "id",
        "title",
        "created_by",
        "species",
        "geocoded_location_locality",
        "encounter_datetime",
        "created",
    )
    list_filter = ("geoprivacy", "created", "encounter_datetime")
    search_fields = (
        "title",
        "text_content",
        "created_by__email",
        "created_by__name",
        "geocoded_location_locality",
    )
    readonly_fields = ("id", "created", "modified", "upvoted_by")
    ordering = ("-created",)

    fieldsets = (
        (
            "Post Information",
            {
                "fields": (
                    "id",
                    "title",
                    "text_content",
                    "created_by",
                    "species",
                    "media",
                    "encounter_datetime",
                )
            },
        ),
        (
            "Location Information",
            {
                "fields": (
                    "geoprivacy",
                    "public_location_latitude",
                    "public_location_longitude",
                    "geocoded_location_locality",
                    "geocoded_location_state",
                    "geocoded_location_country",
                    "geocoded_location_zip_code",
                )
            },
        ),
        (
            "Engagement",
            {
                "fields": ("replies", "upvoted_by"),
            },
        ),
        (
            "Timestamps",
            {
                "fields": ("created", "modified"),
            },
        ),
    )

    def get_queryset(self, request):
        """Optimize queries"""
        qs = super().get_queryset(request)
        return qs.select_related("created_by", "species", "media")


@admin.register(TextComment)
class TextCommentAdmin(admin.ModelAdmin):
    """Admin interface for TextComment model"""

    list_display = ("id", "get_text_preview", "created_by", "get_upvote_count", "created")
    list_filter = ("created",)
    search_fields = ("text_content", "created_by__email", "created_by__name")
    readonly_fields = ("id", "created", "modified", "upvoted_by")
    ordering = ("-created",)

    fieldsets = (
        (
            "Comment Information",
            {
                "fields": (
                    "id",
                    "text_content",
                    "created_by",
                )
            },
        ),
        (
            "Engagement",
            {
                "fields": ("upvoted_by",),
            },
        ),
        (
            "Timestamps",
            {
                "fields": ("created", "modified"),
            },
        ),
    )

    def get_text_preview(self, obj):
        """Show preview of comment text"""
        text = obj.text_content or ""
        return text[:100] + "..." if len(text) > 100 else text

    get_text_preview.short_description = "Comment Preview"

    def get_upvote_count(self, obj):
        """Show number of upvotes"""
        return obj.upvoted_by.count()

    get_upvote_count.short_description = "Upvotes"

    def get_queryset(self, request):
        """Optimize queries"""
        qs = super().get_queryset(request)
        return qs.select_related("created_by").prefetch_related("upvoted_by")


@admin.register(Media)
class MediaAdmin(admin.ModelAdmin):
    """Admin interface for Media model"""

    list_display = ("id", "is_video", "uploaded_by", "file_cloud_path", "created")
    list_filter = ("is_video", "created")
    search_fields = ("file_cloud_path", "uploaded_by__email", "content_hash")
    readonly_fields = ("id", "created", "modified", "content_hash")
    ordering = ("-created",)

    fieldsets = (
        (
            "Media Information",
            {
                "fields": (
                    "id",
                    "is_video",
                    "file_cloud_path",
                    "content_hash",
                    "uploaded_by",
                )
            },
        ),
        (
            "Timestamps",
            {
                "fields": ("created", "modified"),
            },
        ),
    )

    def get_queryset(self, request):
        """Optimize queries"""
        qs = super().get_queryset(request)
        return qs.select_related("uploaded_by")
