export interface Message {
  id: string;
  content: string;
  timestamp: Date;
  sender: 'user' | 'ai';
}

export interface ChatState {
  isOpen: boolean;
  messages: Message[];
}
