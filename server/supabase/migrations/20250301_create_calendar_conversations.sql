-- Create calendar conversation tables for chat history and patch tracking

CREATE TABLE IF NOT EXISTS public.calendar_conversations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES public.Users(id) ON DELETE CASCADE,
  week_id TEXT NOT NULL,

  created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.calendar_conversation_turns (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  conversation_id UUID NOT NULL REFERENCES public.calendar_conversations(id) ON DELETE CASCADE,

  user_message TEXT NOT NULL,
  agent_response TEXT NOT NULL,

  patches JSONB DEFAULT '[]',
  accepted_patch_ids TEXT[] DEFAULT '{}',
  rejected_patch_ids TEXT[] DEFAULT '{}',

  created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_calendar_conversations_user_week
  ON public.calendar_conversations(user_id, week_id);

CREATE INDEX IF NOT EXISTS idx_calendar_conversation_turns_conversation_id
  ON public.calendar_conversation_turns(conversation_id);

CREATE INDEX IF NOT EXISTS idx_calendar_conversation_turns_created_at
  ON public.calendar_conversation_turns(created_at DESC);

-- Enable Row Level Security
ALTER TABLE public.calendar_conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.calendar_conversation_turns ENABLE ROW LEVEL SECURITY;

-- RLS Policies for calendar_conversations
CREATE POLICY "Users can view own conversations"
  ON public.calendar_conversations FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own conversations"
  ON public.calendar_conversations FOR INSERT
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own conversations"
  ON public.calendar_conversations FOR UPDATE
  USING (auth.uid() = user_id);

-- RLS Policies for calendar_conversation_turns
CREATE POLICY "Users can view own turns"
  ON public.calendar_conversation_turns FOR SELECT
  USING (
    EXISTS (
      SELECT 1 FROM public.calendar_conversations
      WHERE id = conversation_id AND user_id = auth.uid()
    )
  );

CREATE POLICY "Users can insert own turns"
  ON public.calendar_conversation_turns FOR INSERT
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM public.calendar_conversations
      WHERE id = conversation_id AND user_id = auth.uid()
    )
  );

CREATE POLICY "Users can update own turns"
  ON public.calendar_conversation_turns FOR UPDATE
  USING (
    EXISTS (
      SELECT 1 FROM public.calendar_conversations
      WHERE id = conversation_id AND user_id = auth.uid()
    )
  );

-- Trigger to auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION public.update_calendar_conversations_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER calendar_conversations_updated_at
  BEFORE UPDATE ON public.calendar_conversations
  FOR EACH ROW
  EXECUTE FUNCTION public.update_calendar_conversations_updated_at();
