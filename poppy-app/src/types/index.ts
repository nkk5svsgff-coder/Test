export interface User {
  id: string;
  name: string;
  age: number;
  bio: string;
  photoUrl: string;       // Hidden until 10 messages exchanged
  voiceIntroUrl: string;  // Voice intro for discovery
  voiceIntroDuration: number; // Duration in seconds
  location: string;
  interests: string[];
  gender: 'female' | 'male' | 'non-binary' | 'other';
  lookingFor: string[];
  verified: boolean;
}

export interface VoiceMessage {
  id: string;
  senderId: string;
  receiverId: string;
  audioUrl: string;
  duration: number;       // Duration in seconds
  timestamp: Date;
  isPlayed: boolean;
  waveform?: number[];    // Amplitude data for visualization
}

export interface Match {
  id: string;
  users: [string, string];
  createdAt: Date;
  lastMessage?: VoiceMessage;
  messageCount: number;
  photosRevealed: boolean; // True when messageCount >= 10
  unreadCount: number;
}

export interface Conversation {
  matchId: string;
  messages: VoiceMessage[];
  messageCount: number;
  photosRevealed: boolean;
}

export interface SwipeAction {
  type: 'like' | 'pass' | 'super_like';
  userId: string;
  timestamp: Date;
}

export type AuthState = {
  isAuthenticated: boolean;
  currentUser: User | null;
};

export type RecordingState = 'idle' | 'recording' | 'recorded' | 'playing';
