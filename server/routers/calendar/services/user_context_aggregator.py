"""
User Context Aggregator Service

Aggregates data from GitHub, Whoop, and Linear integrations to provide
rich context for AI-powered weekly schedule generation.
"""

from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Any
from collections import defaultdict
import logging

from supabase import Client

from integrations.linear_service import fetch_issues, get_valid_access_token

logger = logging.getLogger(__name__)


class UserContextAggregator:
    """Aggregates user data from GitHub, Whoop, and Linear for schedule generation."""

    def __init__(self, supabase_client: Client):
        self.supabase = supabase_client

    def aggregate_week_context(
        self,
        user_id: str,
        week_start: date,
        week_end: date
    ) -> Dict[str, Any]:
        """
        Aggregate all available user context for a specific week.

        Args:
            user_id: User's UUID
            week_start: Start date of the week (Monday)
            week_end: End date of the week (Sunday)

        Returns:
            Dictionary with GitHub, Whoop, and Linear context
        """
        logger.info(f"Aggregating context for user {user_id}, week {week_start} to {week_end}")

        # Check which integrations are connected
        integration_status = self._get_integration_status(user_id)

        context = {
            "integration_status": integration_status,
            "week_range": {
                "start": week_start.isoformat(),
                "end": week_end.isoformat()
            }
        }

        # Aggregate each data source if connected
        if integration_status.get("has_github"):
            context["github"] = self._get_github_context(user_id, week_start, week_end)

        if integration_status.get("has_whoop"):
            context["whoop"] = self._get_whoop_context(user_id, week_start, week_end)

        if integration_status.get("has_linear"):
            context["linear"] = self._get_linear_context(user_id, week_start, week_end)

        return context

    def _get_integration_status(self, user_id: str) -> Dict[str, bool]:
        """Check which integrations are connected for the user."""
        try:
            response = self.supabase.table("Users").select(
                "has_github, has_whoop, has_linear"
            ).eq("id", user_id).single().execute()

            if response.data:
                return {
                    "has_github": response.data.get("has_github", False),
                    "has_whoop": response.data.get("has_whoop", False),
                    "has_linear": response.data.get("has_linear", False)
                }
        except Exception as e:
            logger.error(f"Error checking integration status: {e}")

        return {"has_github": False, "has_whoop": False, "has_linear": False}

    def _get_github_context(
        self,
        user_id: str,
        week_start: date,
        week_end: date
    ) -> Dict[str, Any]:
        """
        Aggregate GitHub commit data for the week.

        Returns work patterns, active repositories, and recent activity.
        """
        try:
            # Query commits in the past 7-14 days to understand patterns
            lookback_start = week_start - timedelta(days=14)

            response = self.supabase.table("github_commits").select(
                "sha, repo_full_name, authored_at, message_headline, additions, deletions, total_changes"
            ).eq("user_id", user_id).gte(
                "authored_at", lookback_start.isoformat()
            ).order("authored_at", desc=True).execute()

            if not response.data:
                return {
                    "has_data": False,
                    "message": "No recent GitHub activity found"
                }

            commits = response.data

            # Aggregate statistics
            commits_by_day = defaultdict(int)
            commits_by_repo = defaultdict(int)
            total_additions = 0
            total_deletions = 0
            recent_messages = []

            for commit in commits:
                # Parse date
                authored_at = datetime.fromisoformat(commit["authored_at"].replace("Z", "+00:00"))
                day = authored_at.date()

                commits_by_day[day.isoformat()] += 1
                commits_by_repo[commit["repo_full_name"]] += 1

                total_additions += commit.get("additions", 0) or 0
                total_deletions += commit.get("deletions", 0) or 0

                # Collect recent commit messages (last 5)
                if len(recent_messages) < 5:
                    recent_messages.append({
                        "date": day.isoformat(),
                        "repo": commit["repo_full_name"],
                        "message": commit["message_headline"]
                    })

            # Find most active repositories
            active_repos = sorted(
                commits_by_repo.items(),
                key=lambda x: x[1],
                reverse=True
            )[:3]

            # Calculate average commits per day
            days_with_commits = len(commits_by_day)
            avg_commits_per_active_day = len(commits) / max(days_with_commits, 1)

            return {
                "has_data": True,
                "total_commits": len(commits),
                "days_with_activity": days_with_commits,
                "avg_commits_per_active_day": round(avg_commits_per_active_day, 1),
                "total_lines_changed": total_additions + total_deletions,
                "additions": total_additions,
                "deletions": total_deletions,
                "active_repositories": [
                    {"repo": repo, "commits": count} for repo, count in active_repos
                ],
                "recent_work": recent_messages,
                "commits_by_day": dict(commits_by_day)
            }

        except Exception as e:
            logger.error(f"Error aggregating GitHub context: {e}")
            return {
                "has_data": False,
                "error": str(e)
            }

    def _get_whoop_context(
        self,
        user_id: str,
        week_start: date,
        week_end: date
    ) -> Dict[str, Any]:
        """
        Aggregate Whoop health and fitness data for the week.

        Returns recovery scores, sleep patterns, and workout schedule.
        """
        try:
            # Query data for the past 14 days to understand patterns
            lookback_start = week_start - timedelta(days=14)

            # Get recovery data
            recoveries = self._get_whoop_recoveries(user_id, lookback_start, week_end)

            # Get sleep data
            sleep_data = self._get_whoop_sleep(user_id, lookback_start, week_end)

            # Get workout data
            workouts = self._get_whoop_workouts(user_id, lookback_start, week_end)

            if not recoveries and not sleep_data and not workouts:
                return {
                    "has_data": False,
                    "message": "No Whoop data found in date range"
                }

            # Aggregate recovery metrics
            recovery_scores = [r["recovery_score"] for r in recoveries if r["recovery_score"] is not None]
            avg_recovery = sum(recovery_scores) / len(recovery_scores) if recovery_scores else None

            # Aggregate sleep metrics
            sleep_durations = []
            sleep_performances = []
            for sleep in sleep_data:
                if sleep["end_time"] and sleep["start_time"] and not sleep.get("nap"):
                    start = datetime.fromisoformat(sleep["start_time"].replace("Z", "+00:00"))
                    end = datetime.fromisoformat(sleep["end_time"].replace("Z", "+00:00"))
                    duration_hours = (end - start).total_seconds() / 3600
                    sleep_durations.append(duration_hours)

                    if sleep["sleep_performance_percentage"]:
                        sleep_performances.append(sleep["sleep_performance_percentage"])

            avg_sleep_hours = sum(sleep_durations) / len(sleep_durations) if sleep_durations else None
            avg_sleep_quality = sum(sleep_performances) / len(sleep_performances) if sleep_performances else None

            # Aggregate workout patterns
            workout_times = defaultdict(int)  # hour -> count
            workout_types = defaultdict(int)

            for workout in workouts:
                if workout["start_time"]:
                    start = datetime.fromisoformat(workout["start_time"].replace("Z", "+00:00"))
                    hour = start.hour
                    workout_times[hour] += 1

                    sport = workout.get("sport_name", "Unknown")
                    workout_types[sport] += 1

            # Find typical workout time
            typical_workout_hour = max(workout_times.items(), key=lambda x: x[1])[0] if workout_times else None

            return {
                "has_data": True,
                "recovery": {
                    "avg_score": round(avg_recovery, 1) if avg_recovery else None,
                    "recent_scores": [
                        {
                            "date": r.get("cycle_start", "")[:10] if r.get("cycle_start") else None,
                            "score": r["recovery_score"]
                        }
                        for r in recoveries[-7:] if r["recovery_score"] is not None
                    ]
                },
                "sleep": {
                    "avg_duration_hours": round(avg_sleep_hours, 1) if avg_sleep_hours else None,
                    "avg_quality_percentage": round(avg_sleep_quality, 1) if avg_sleep_quality else None,
                    "nights_tracked": len(sleep_durations)
                },
                "workouts": {
                    "total_workouts": len(workouts),
                    "typical_time_hour": typical_workout_hour,
                    "workout_types": dict(workout_types),
                    "recent_workouts": [
                        {
                            "date": w.get("start_time", "")[:10] if w.get("start_time") else None,
                            "sport": w.get("sport_name"),
                            "strain": w.get("strain")
                        }
                        for w in workouts[-5:]
                    ]
                }
            }

        except Exception as e:
            logger.error(f"Error aggregating Whoop context: {e}")
            return {
                "has_data": False,
                "error": str(e)
            }

    def _get_whoop_recoveries(
        self,
        user_id: str,
        start_date: date,
        end_date: date
    ) -> List[Dict]:
        """Query Whoop recovery data."""
        try:
            response = self.supabase.table("whoop_recoveries").select(
                "whoop_cycle_id, recovery_score, resting_heart_rate, hrv_rmssd_milli"
            ).eq("user_id", user_id).execute()

            # Filter by date using cycle_start from whoop_cycles
            if response.data:
                cycle_ids = [r["whoop_cycle_id"] for r in response.data]
                cycles = self.supabase.table("whoop_cycles").select(
                    "whoop_cycle_id, cycle_start"
                ).in_("whoop_cycle_id", cycle_ids).gte(
                    "cycle_start", start_date.isoformat()
                ).lte("cycle_start", end_date.isoformat()).execute()

                valid_cycle_ids = {c["whoop_cycle_id"] for c in cycles.data} if cycles.data else set()

                # Add cycle_start to recovery data
                cycle_map = {c["whoop_cycle_id"]: c["cycle_start"] for c in cycles.data} if cycles.data else {}

                filtered = []
                for r in response.data:
                    if r["whoop_cycle_id"] in valid_cycle_ids:
                        r["cycle_start"] = cycle_map.get(r["whoop_cycle_id"])
                        filtered.append(r)

                return filtered

            return []
        except Exception as e:
            logger.error(f"Error querying Whoop recoveries: {e}")
            return []

    def _get_whoop_sleep(
        self,
        user_id: str,
        start_date: date,
        end_date: date
    ) -> List[Dict]:
        """Query Whoop sleep data."""
        try:
            response = self.supabase.table("whoop_sleep").select(
                "whoop_sleep_id, start_time, end_time, nap, sleep_performance_percentage"
            ).eq("user_id", user_id).gte(
                "start_time", start_date.isoformat()
            ).lte("end_time", end_date.isoformat()).execute()

            return response.data if response.data else []
        except Exception as e:
            logger.error(f"Error querying Whoop sleep: {e}")
            return []

    def _get_whoop_workouts(
        self,
        user_id: str,
        start_date: date,
        end_date: date
    ) -> List[Dict]:
        """Query Whoop workout data."""
        try:
            response = self.supabase.table("whoop_workouts").select(
                "whoop_workout_id, start_time, end_time, sport_name, strain"
            ).eq("user_id", user_id).gte(
                "start_time", start_date.isoformat()
            ).lte("end_time", end_date.isoformat()).execute()

            return response.data if response.data else []
        except Exception as e:
            logger.error(f"Error querying Whoop workouts: {e}")
            return []

    def _get_linear_context(
        self,
        user_id: str,
        week_start: date,
        week_end: date
    ) -> Dict[str, Any]:
        """
        Fetch Linear issues on-demand via GraphQL.

        Returns tasks, priorities, and deadlines relevant to the week.
        """
        try:
            # Get valid access token (will auto-refresh if needed)
            try:
                access_token = get_valid_access_token(user_id)
            except Exception as token_error:
                logger.warning(f"Could not get Linear access token: {token_error}")
                return {
                    "has_data": False,
                    "message": "Linear integration not properly configured"
                }

            # Fetch issues assigned to user
            issues_response = fetch_issues(
                user_id=user_id,
                filters={"assignee": "me"}
            )

            if not issues_response or "nodes" not in issues_response:
                return {
                    "has_data": False,
                    "message": "No Linear issues found"
                }

            issues = issues_response["nodes"]

            # Filter and categorize issues
            open_issues = []
            upcoming_deadlines = []
            high_priority_tasks = []
            projects = set()

            for issue in issues:
                # Skip completed/canceled
                state_type = issue.get("state", {}).get("type", "").lower()
                if state_type in ["completed", "canceled"]:
                    continue

                open_issues.append(issue)

                # Check priority (1=urgent, 2=high, 3=medium, 4=low, 0=none)
                priority = issue.get("priority", 0)
                if priority in [1, 2]:
                    high_priority_tasks.append({
                        "identifier": issue.get("identifier"),
                        "title": issue.get("title"),
                        "priority": priority
                    })

                # Check deadlines
                due_date = issue.get("dueDate")
                if due_date:
                    due = datetime.fromisoformat(due_date.replace("Z", "+00:00")).date()
                    # Include deadlines within 2 weeks
                    if due <= week_end + timedelta(days=14):
                        upcoming_deadlines.append({
                            "identifier": issue.get("identifier"),
                            "title": issue.get("title"),
                            "due_date": due.isoformat(),
                            "days_until_due": (due - week_start).days
                        })

                # Track projects
                project_name = issue.get("project", {}).get("name")
                if project_name:
                    projects.add(project_name)

            # Sort deadlines by date
            upcoming_deadlines.sort(key=lambda x: x["due_date"])

            # Priority distribution
            priority_counts = defaultdict(int)
            for issue in open_issues:
                priority = issue.get("priority", 0)
                priority_name = {
                    1: "urgent",
                    2: "high",
                    3: "medium",
                    4: "low",
                    0: "none"
                }.get(priority, "unknown")
                priority_counts[priority_name] += 1

            return {
                "has_data": True,
                "total_open_issues": len(open_issues),
                "high_priority_count": len(high_priority_tasks),
                "upcoming_deadlines": upcoming_deadlines[:5],  # Top 5
                "high_priority_tasks": high_priority_tasks[:5],  # Top 5
                "active_projects": list(projects),
                "priority_distribution": dict(priority_counts),
                "state_distribution": {
                    "backlog": sum(1 for i in open_issues if i.get("state", {}).get("type", "").lower() == "backlog"),
                    "started": sum(1 for i in open_issues if i.get("state", {}).get("type", "").lower() == "started"),
                    "unstarted": sum(1 for i in open_issues if i.get("state", {}).get("type", "").lower() == "unstarted")
                }
            }

        except Exception as e:
            logger.error(f"Error aggregating Linear context: {e}")
            return {
                "has_data": False,
                "error": str(e)
            }

    def format_context_for_prompt(self, context: Dict[str, Any]) -> str:
        """
        Format the aggregated context into a readable string for LLM prompt injection.

        Args:
            context: The aggregated context dictionary

        Returns:
            Formatted string ready to inject into system prompt
        """
        sections = []

        # GitHub section
        if "github" in context and context["github"].get("has_data"):
            gh = context["github"]
            section = "RECENT CODING ACTIVITY (GitHub):\n"
            section += f"- Total commits (past 2 weeks): {gh['total_commits']}\n"
            section += f"- Days with activity: {gh['days_with_activity']}\n"
            section += f"- Average commits per active day: {gh['avg_commits_per_active_day']}\n"
            section += f"- Total lines changed: {gh['total_lines_changed']:,} ({gh['additions']:,} additions, {gh['deletions']:,} deletions)\n"

            if gh.get("active_repositories"):
                section += "- Most active repositories:\n"
                for repo in gh["active_repositories"]:
                    section += f"  • {repo['repo']}: {repo['commits']} commits\n"

            if gh.get("recent_work"):
                section += "- Recent work:\n"
                for work in gh["recent_work"]:
                    section += f"  • [{work['date']}] {work['repo']}: {work['message']}\n"

            sections.append(section)

        # Whoop section
        if "whoop" in context and context["whoop"].get("has_data"):
            whoop = context["whoop"]
            section = "HEALTH & ENERGY DATA (Whoop):\n"

            if whoop.get("recovery", {}).get("avg_score"):
                avg_recovery = whoop["recovery"]["avg_score"]
                section += f"- Average recovery score: {avg_recovery}% "
                if avg_recovery >= 67:
                    section += "(High - ready for intense work)\n"
                elif avg_recovery >= 34:
                    section += "(Moderate - balanced schedule recommended)\n"
                else:
                    section += "(Low - prioritize rest and recovery)\n"

                if whoop["recovery"].get("recent_scores"):
                    section += "- Recent recovery scores:\n"
                    for score in whoop["recovery"]["recent_scores"]:
                        section += f"  • {score['date']}: {score['score']}%\n"

            if whoop.get("sleep", {}).get("avg_duration_hours"):
                section += f"- Average sleep: {whoop['sleep']['avg_duration_hours']} hours/night\n"
                if whoop['sleep'].get('avg_quality_percentage'):
                    section += f"- Sleep quality: {whoop['sleep']['avg_quality_percentage']}%\n"

            if whoop.get("workouts"):
                section += f"- Recent workouts: {whoop['workouts']['total_workouts']} sessions\n"
                if whoop['workouts'].get('typical_time_hour') is not None:
                    hour = whoop['workouts']['typical_time_hour']
                    time_str = f"{hour}:00" if hour < 12 else f"{hour-12 if hour > 12 else hour}:00 {'AM' if hour < 12 else 'PM'}"
                    section += f"- Typical workout time: {time_str}\n"

                if whoop['workouts'].get('workout_types'):
                    types = ", ".join(whoop['workouts']['workout_types'].keys())
                    section += f"- Workout types: {types}\n"

            sections.append(section)

        # Linear section
        if "linear" in context and context["linear"].get("has_data"):
            linear = context["linear"]
            section = "TASKS & PROJECTS (Linear):\n"
            section += f"- Total open issues: {linear['total_open_issues']}\n"
            section += f"- High priority tasks: {linear['high_priority_count']}\n"

            if linear.get("upcoming_deadlines"):
                section += "- Upcoming deadlines:\n"
                for deadline in linear["upcoming_deadlines"]:
                    days = deadline["days_until_due"]
                    urgency = "⚠️ URGENT" if days <= 2 else "Soon" if days <= 7 else "Upcoming"
                    section += f"  • [{urgency}] {deadline['identifier']}: {deadline['title']} (due {deadline['due_date']}, in {days} days)\n"

            if linear.get("high_priority_tasks"):
                section += "- High priority tasks to schedule:\n"
                for task in linear["high_priority_tasks"]:
                    priority_label = "🔴 Urgent" if task["priority"] == 1 else "🟠 High"
                    section += f"  • [{priority_label}] {task['identifier']}: {task['title']}\n"

            if linear.get("active_projects"):
                projects = ", ".join(linear["active_projects"])
                section += f"- Active projects: {projects}\n"

            if linear.get("priority_distribution"):
                section += "- Priority distribution: "
                dist = linear["priority_distribution"]
                parts = [f"{count} {priority}" for priority, count in dist.items() if count > 0]
                section += ", ".join(parts) + "\n"

            sections.append(section)

        # Combine all sections
        if sections:
            header = "=" * 80 + "\n"
            header += "USER CONTEXT DATA (for personalized scheduling)\n"
            header += "=" * 80 + "\n\n"
            return header + "\n".join(sections)
        else:
            return ""
