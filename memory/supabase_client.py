"""
Supabase memory layer — all database reads and writes for Guardian.

Required Supabase tables (run this SQL in your Supabase dashboard):

-- users
create table users (
  user_id text primary key,
  created_at timestamptz default now()
);

-- analysis_runs
create table analysis_runs (
  run_id text primary key,
  user_id text references users(user_id),
  created_at timestamptz default now(),
  health_score integer,
  total_monthly_at_risk float,
  executive_summary text,
  status text default 'pending'
);

-- findings
create table findings (
  id uuid default gen_random_uuid() primary key,
  run_id text references analysis_runs(run_id),
  user_id text references users(user_id),
  type text,           -- 'subscription' | 'reward' | 'budget_goals'
  subtype text,
  merchant text,
  rupee_impact float,
  severity text,
  explanation text,
  action text,
  resolved boolean default false,
  created_at timestamptz default now()
);

-- resolved_actions
create table resolved_actions (
  id uuid default gen_random_uuid() primary key,
  finding_id uuid references findings(id),
  user_id text,
  resolved_at timestamptz default now(),
  rupee_saved float,
  notes text
);

-- user_income (NEW)
create table user_income (
  user_id        text primary key references users(user_id),
  monthly_income float not null,
  updated_at     timestamptz default now()
);

-- goals (NEW)
create table goals (
  goal_id        uuid default gen_random_uuid() primary key,
  user_id        text references users(user_id),
  name           text not null,
  goal_type      text not null,
  target_amount  float not null,
  saved_amount   float default 0,
  surplus_pct    float not null,
  is_active      bool default true,
  created_at     timestamptz default now()
);

-- goal_snapshots (NEW)
create table goal_snapshots (
  id                   uuid default gen_random_uuid() primary key,
  run_id               text references analysis_runs(run_id),
  goal_id              uuid references goals(goal_id),
  months_at_current    float,
  months_at_balanced   float,
  months_at_conservative float,
  biggest_lever_category text,
  biggest_lever_days_saved int,
  snapshot_date        timestamptz default now()
);
-- user_provider_config (NEW)
create table user_provider_config (
  user_id       text primary key references users(user_id),
  provider      text not null,    -- 'google' | 'openai' | 'openrouter' | 'mistral'
  model_id      text not null,    -- the selected model string
  api_key       text not null,    -- stored as-is (user's own key, BYOK)
  exa_api_key   text default '',
  updated_at    timestamptz default now()
);
"""

from __future__ import annotations

import logging
from typing import Optional
from datetime import datetime

from supabase import create_client, Client

from config import settings

logger = logging.getLogger(__name__)


class SupabaseMemory:
    """Handles all Supabase database operations for Guardian. Singleton."""
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(SupabaseMemory, cls).__new__(cls, *args, **kwargs)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if getattr(self, "_initialized", False):
            return
        self._initialized = True
        
        self._client: Optional[Client] = None
        self._fallback_income: dict = {}  # In-memory fallback when Supabase tables missing
        self._fallback_goals: dict = {}   # In-memory fallback when Supabase tables missing
        if settings.supabase_url and settings.supabase_key:
            try:
                print(f"[Supabase] Attempting connection to {settings.supabase_url}...")
                self._client = create_client(settings.supabase_url, settings.supabase_key)
                print(f"[Supabase] Connection established successfully.")
            except Exception as e:
                print(f"[Supabase] CRITICAL: Connection failed: {e}")
                logger.warning(f"Could not connect to Supabase: {e}. Persistence disabled.")
        else:
            print("[Supabase] WARNING: SUPABASE_URL or SUPABASE_KEY missing in .env")
            logger.info("Supabase credentials not set — persistence disabled.")

    @property
    def _is_connected(self) -> bool:
        return self._client is not None

    async def get_provider_config(self, user_id: str) -> dict | None:
        """Returns stored provider config or None if not set."""
        if not self._is_connected:
            return None
        try:
            result = self._client.table("user_provider_config")\
                .select("*")\
                .eq("user_id", user_id)\
                .single()\
                .execute()
            return result.data if result.data else None
        except Exception:
            return None

    async def save_provider_config(
        self,
        user_id: str,
        provider: str,
        model_id: str,
        api_key: str,
        exa_api_key: str = ""
    ) -> None:
        if not self._is_connected:
            return
        try:
            self._client.table("user_provider_config").upsert({
                "user_id": user_id,
                "provider": provider,
                "model_id": model_id,
                "api_key": api_key,
                "exa_api_key": exa_api_key,
                "updated_at": datetime.utcnow().isoformat()
            }).execute()
        except Exception as e:
            logger.error(f"Failed to save provider config: {e}")

    # ------------------------------------------------------------------
    # Users & Income
    # ------------------------------------------------------------------
    def upsert_user(self, user_id: str) -> None:
        """Create or update a user record."""
        if not self._is_connected:
            return
        try:
            self._client.table("users").upsert(
                {"user_id": user_id},
                on_conflict="user_id",
            ).execute()
        except Exception as e:
            logger.error(f"Failed to upsert user {user_id}: {e}")

    def get_user_income(self, user_id: str) -> float:
        """Fetch the user's manually entered monthly income."""
        if not self._is_connected:
            return self._fallback_income.get(user_id, 0.0)
        try:
            result = self._client.table("user_income")\
                .select("monthly_income")\
                .eq("user_id", user_id)\
                .execute()
            val = result.data[0]["monthly_income"] if result.data else 0.0
            return val
        except Exception as e:
            logger.warning(f"Supabase user_income read failed, using fallback: {e}")
            return self._fallback_income.get(user_id, 0.0)

    def set_user_income(self, user_id: str, monthly_income: float) -> None:
        """Set the user's monthly income."""
        self.upsert_user(user_id)
        self._fallback_income[user_id] = monthly_income
        print(f"[Supabase] Income ₹{monthly_income} stored for {user_id} (fallback stored)")
        if not self._is_connected:
            return
        try:
            self._client.table("user_income").upsert(
                {"user_id": user_id, "monthly_income": monthly_income},
                on_conflict="user_id",
            ).execute()
            print(f"[Supabase] Income persisted to DB")
        except Exception as e:
            logger.warning(f"Supabase income write failed, using fallback: {e}")

    def purge_user_data(self, user_id: str) -> None:
        """Purge all user specific data like income and goals."""
        if user_id in self._fallback_income:
            del self._fallback_income[user_id]
        if user_id in self._fallback_goals:
            del self._fallback_goals[user_id]
        
        if not self._is_connected: return
        try:
            # We delete goals and income. 
            # First, fetch goal IDs to delete dependent snapshots and avoid foreign key errors.
            goals_res = self._client.table("goals").select("goal_id").eq("user_id", user_id).execute()
            if goals_res.data:
                goal_ids = [g["goal_id"] for g in goals_res.data]
                self._client.table("goal_snapshots").delete().in_("goal_id", goal_ids).execute()
                self._client.table("goals").delete().in_("goal_id", goal_ids).execute()
                
            self._client.table("user_income").delete().eq("user_id", user_id).execute()
            self._client.table("user_provider_config").delete().eq("user_id", user_id).execute()
            print(f"[Supabase] Purged income, goals, and provider config for {user_id}")
        except Exception as e:
            logger.warning(f"Failed to purge user data: {e}")

    # ------------------------------------------------------------------
    # Goals
    # ------------------------------------------------------------------
    def get_active_goals(self, user_id: str) -> list[dict]:
        """Fetch all active financial goals for a user."""
        if not self._is_connected:
            return self._fallback_goals.get(user_id, [])
        try:
            result = self._client.table("goals")\
                .select("*")\
                .eq("user_id", user_id)\
                .eq("is_active", True)\
                .execute()
            if result.data:
                return result.data
            return self._fallback_goals.get(user_id, [])
        except Exception as e:
            logger.warning(f"Supabase goals read failed, using fallback: {e}")
            return self._fallback_goals.get(user_id, [])

    def upsert_goal(
        self, 
        user_id: str, 
        goal_name: str, 
        target_amount: float, 
        saved_amount: float, 
        priority: str, 
        goal_id: str = None
    ) -> str:
        """Create or update a financial goal."""
        import uuid
        # Map priority to surplus_pct
        priority_str = str(priority).lower()
        pct_map = {"high": 0.5, "medium": 0.3, "low": 0.2, "1": 0.5, "2": 0.3, "3": 0.2}
        surplus_pct = pct_map.get(priority_str, 0.3)
        
        generated_id = goal_id or str(uuid.uuid4())
        
        goal_dict = {
            "goal_id": generated_id,
            "user_id": user_id,
            "name": goal_name,
            "target_amount": target_amount,
            "saved_amount": saved_amount,
            "goal_type": "saving",
            "surplus_pct": surplus_pct,
            "is_active": True
        }
        
        # Always store in fallback
        if user_id not in self._fallback_goals:
            self._fallback_goals[user_id] = []
        # Replace if exists, else append
        existing = [g for g in self._fallback_goals[user_id] if g["goal_id"] == generated_id]
        if existing:
            self._fallback_goals[user_id] = [g if g["goal_id"] != generated_id else goal_dict for g in self._fallback_goals[user_id]]
        else:
            self._fallback_goals[user_id].append(goal_dict)
        print(f"[Supabase] Goal '{goal_name}' stored for {user_id} (fallback stored, id={generated_id})")
        
        if not self._is_connected:
            return generated_id
        try:
            payload = {**goal_dict}
            result = self._client.table("goals").upsert(payload).execute()
            db_id = result.data[0]["goal_id"] if result.data else generated_id
            print(f"[Supabase] Goal persisted to DB: {db_id}")
            return db_id
        except Exception as e:
            logger.warning(f"Supabase goals write failed, using fallback: {e}")
            return generated_id

    def delete_goal(self, goal_id: str) -> None:
        """Remove a goal by ID."""
        # Remove from all fallback lists
        for uid in self._fallback_goals:
            self._fallback_goals[uid] = [g for g in self._fallback_goals[uid] if g["goal_id"] != goal_id]
        print(f"[Supabase] Goal {goal_id} deleted from fallback")
        if not self._is_connected: return
        try:
            self._client.table("goals").update({"is_active": False}).eq("goal_id", goal_id).execute()
            print(f"[Supabase] Goal {goal_id} deactivated in DB")
        except Exception as e:
            logger.warning(f"Supabase goal delete failed: {e}")

    def update_goal_saved_amount(self, goal_id: str, amount: float) -> None:
        """Manually update the amount saved towards a goal."""
        if not self._is_connected: return
        try:
            self._client.table("goals").update({"saved_amount": amount}).eq("goal_id", goal_id).execute()
        except Exception as e:
            logger.error(f"Failed to update goal saved amount: {e}")

    def deactivate_goal(self, goal_id: str) -> None:
        """Mark a goal as inactive."""
        if not self._is_connected: return
        try:
            self._client.table("goals").update({"is_active": False}).eq("goal_id", goal_id).execute()
        except Exception as e:
            logger.error(f"Failed to deactivate goal: {e}")

    def save_goal_snapshots(self, run_id: str, snapshots: list[dict]) -> None:
        """Save point-in-time snapshots of goal progress from an analysis run."""
        if not self._is_connected or not snapshots: return
        try:
            rows = []
            for s in snapshots:
                rows.append({
                    "run_id": run_id,
                    "goal_id": s.get("goal_id"),
                    "months_at_current": s.get("current_pace_months"),
                    "months_at_balanced": s.get("balanced_months"),
                    "months_at_conservative": s.get("conservative_months"),
                    "biggest_lever_category": s.get("biggest_lever_category"),
                    "biggest_lever_days_saved": s.get("biggest_lever_days_saved")
                })
            self._client.table("goal_snapshots").insert(rows).execute()
        except Exception as e:
            logger.error(f"Failed to save goal snapshots: {e}")

    def get_goal_history(self, goal_id: str) -> list[dict]:
        """Fetch history of snapshots for a specific goal (for trending)."""
        if not self._is_connected: return []
        try:
            result = self._client.table("goal_snapshots")\
                .select("*")\
                .eq("goal_id", goal_id)\
                .order("snapshot_date", desc=True)\
                .execute()
            return result.data or []
        except Exception as e:
            logger.error(f"Failed to fetch goal history: {e}")
            return []

    # ------------------------------------------------------------------
    # Analysis Runs
    # ------------------------------------------------------------------
    def create_run(self, run_id: str, user_id: str) -> None:
        """Create a new analysis run record."""
        if not self._is_connected:
            return
        try:
            self._client.table("analysis_runs").insert({
                "run_id": run_id,
                "user_id": user_id,
                "status": "pending",
            }).execute()
        except Exception as e:
            logger.error(f"Failed to create run {run_id}: {e}")

    def update_run_summary(
        self,
        run_id: str,
        health_score: int,
        total_at_risk: float,
        summary: str,
    ) -> None:
        """Update a run with final results."""
        if not self._is_connected:
            return
        try:
            self._client.table("analysis_runs").update({
                "health_score": health_score,
                "total_monthly_at_risk": total_at_risk,
                "executive_summary": summary,
                "status": "completed",
            }).eq("run_id", run_id).execute()
        except Exception as e:
            logger.error(f"Failed to update run {run_id}: {e}")

    # ------------------------------------------------------------------
    # Findings
    # ------------------------------------------------------------------
    def save_findings(self, run_id: str, user_id: str, findings: list[dict]) -> None:
        """Save a batch of findings to Supabase."""
        if not self._is_connected:
            return
        try:
            rows = []
            for f in findings:
                # Compute rupee_impact from available fields
                rupee_impact = (
                    f.get("rupee_impact")
                    or f.get("annual_cost")
                    or f.get("total_charged")
                    or f.get("monthly_amount", 0) * 12
                )
                rows.append({
                    "run_id": run_id,
                    "user_id": user_id,
                    "type": f.get("type", "unknown"),
                    "subtype": f.get("subtype", ""),
                    "merchant": f.get("merchant", f.get("title", "")),
                    "rupee_impact": rupee_impact,
                    "severity": f.get("severity", "low"),
                    "explanation": f.get("explanation", f.get("description", "")),
                    "action": f.get("action", f.get("recommended_action", "")),
                    "resolved": False,
                })

            if rows:
                self._client.table("findings").insert(rows).execute()
        except Exception as e:
            logger.error(f"Failed to save findings for run {run_id}: {e}")

    def get_findings(self, user_id: str, resolved: bool = False) -> list[dict]:
        """Get findings for a user, filtered by resolved status."""
        if not self._is_connected:
            return []
        try:
            response = (
                self._client.table("findings")
                .select("*")
                .eq("user_id", user_id)
                .eq("resolved", resolved)
                .order("created_at", desc=True)
                .execute()
            )
            return response.data or []
        except Exception as e:
            logger.error(f"Failed to get findings for user {user_id}: {e}")
            return []

    def get_run_history(self, user_id: str, limit: int = 6) -> list[dict]:
        """Get the last N analysis runs for a user."""
        if not self._is_connected:
            return []
        try:
            response = (
                self._client.table("analysis_runs")
                .select("*")
                .eq("user_id", user_id)
                .order("created_at", desc=True)
                .limit(limit)
                .execute()
            )
            return response.data or []
        except Exception as e:
            logger.error(f"Failed to get run history for user {user_id}: {e}")
            return []

    def resolve_finding(
        self,
        finding_id: str,
        rupee_saved: float,
        notes: str = "",
    ) -> None:
        """Mark a finding as resolved and log the action."""
        if not self._is_connected:
            return
        try:
            # Mark finding as resolved
            self._client.table("findings").update(
                {"resolved": True}
            ).eq("id", finding_id).execute()

            # Get user_id from finding
            finding_response = (
                self._client.table("findings")
                .select("user_id")
                .eq("id", finding_id)
                .execute()
            )
            user_id = ""
            if finding_response.data:
                user_id = finding_response.data[0].get("user_id", "")

            # Log resolved action
            self._client.table("resolved_actions").insert({
                "finding_id": finding_id,
                "user_id": user_id,
                "rupee_saved": rupee_saved,
                "notes": notes,
            }).execute()
        except Exception as e:
            logger.error(f"Failed to resolve finding {finding_id}: {e}")

    def get_health_score_history(self, user_id: str) -> list[dict]:
        """Get health score trend for a user across all runs."""
        if not self._is_connected:
            return []
        try:
            response = (
                self._client.table("analysis_runs")
                .select("run_id, created_at, health_score, total_monthly_at_risk")
                .eq("user_id", user_id)
                .eq("status", "completed")
                .order("created_at", desc=True)
                .execute()
            )
            return response.data or []
        except Exception as e:
            logger.error(f"Failed to get health score history for user {user_id}: {e}")
            return []

    def get_user_context_summary(self, user_id: str) -> str:
        """
        Builds a lightweight financial context string for the chatbot.
        Pulls from the latest analysis run for this user.
        Returns a formatted string — empty string if no analysis exists.
        """
        try:
            # Get latest run
            runs = self.get_run_history(user_id, limit=1)
            if not runs:
                return ""

            latest_run = runs[0]

            # Get unresolved findings
            findings = self.get_findings(user_id, resolved=False)
            high_count = sum(1 for f in findings if f.get("severity") == "high")

            # Get top 3 merchants from findings
            merchants = [f.get("merchant", "") for f in findings if f.get("merchant")]
            top_merchants = list(dict.fromkeys(merchants))[:5]  # deduplicated

            # Build category breakdown
            category_lines = []
            if latest_run.get('analysis_data'):
                # Some runs might store the full forecast in analysis_data
                data = latest_run['analysis_data']
                if 'budget_forecast' in data:
                    forecast = data['budget_forecast']
                    for cat, val in list(forecast.get('by_category', {}).items())[:6]:
                        category_lines.append(f"- {cat}: ₹{val:,.0f}")

            context = (
                f"LATEST ANALYSIS DATA (Run ID: {latest_run.get('run_id')}):\n"
                f"Financial health score: {latest_run.get('health_score', 'unknown')}/100\n"
                f"Total monthly spend: ₹{latest_run.get('total_monthly_at_risk', 0):,.0f}\n"
                f"High severity issues: {high_count}\n"
                f"Top spending categories:\n{chr(10).join(category_lines) if category_lines else 'No category data available'}\n"
                f"Key merchants detected: {', '.join(top_merchants) if top_merchants else 'None'}\n"
            )
            if top_merchants:
                context += f"Key flagged merchants: {', '.join(top_merchants)}\n"

            return context.strip()

        except Exception as e:
            logger.warning(f"Could not build user context summary: {e}")
            return ""

