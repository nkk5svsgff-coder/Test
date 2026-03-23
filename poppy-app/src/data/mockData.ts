import { User, Match, VoiceMessage, Conversation } from '../types';

// Placeholder voice waveform data
const generateWaveform = (length: number = 30): number[] =>
  Array.from({ length }, () => Math.random() * 0.8 + 0.1);

export const currentUser: User = {
  id: 'current-user',
  name: 'You',
  age: 26,
  bio: 'Looking for meaningful connections through voice',
  photoUrl: 'https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=400',
  voiceIntroUrl: '',
  voiceIntroDistance: 0,
  voiceIntroDuration: 15,
  location: 'New York, NY',
  interests: ['Music', 'Travel', 'Cooking', 'Yoga'],
  gender: 'female',
  lookingFor: ['male', 'female'],
  verified: true,
} as any;

export const discoverProfiles: User[] = [
  {
    id: 'user-1',
    name: 'Emma',
    age: 24,
    bio: 'Singer-songwriter who loves sunsets and deep conversations',
    photoUrl: 'https://images.unsplash.com/photo-1524504388940-b1c1722653e1?w=400',
    voiceIntroUrl: 'voice-1.m4a',
    voiceIntroDuration: 18,
    location: 'Brooklyn, NY',
    interests: ['Music', 'Art', 'Poetry', 'Coffee'],
    gender: 'female',
    lookingFor: ['male', 'female'],
    verified: true,
  },
  {
    id: 'user-2',
    name: 'Sofia',
    age: 27,
    bio: 'Yoga instructor with a passion for travel and good food',
    photoUrl: 'https://images.unsplash.com/photo-1517841905240-472988babdf9?w=400',
    voiceIntroUrl: 'voice-2.m4a',
    voiceIntroDuration: 22,
    location: 'Manhattan, NY',
    interests: ['Yoga', 'Travel', 'Cooking', 'Photography'],
    gender: 'female',
    lookingFor: ['male'],
    verified: true,
  },
  {
    id: 'user-3',
    name: 'James',
    age: 29,
    bio: 'Chef by day, musician by night. Let\'s share stories!',
    photoUrl: 'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=400',
    voiceIntroUrl: 'voice-3.m4a',
    voiceIntroDuration: 14,
    location: 'Queens, NY',
    interests: ['Cooking', 'Music', 'Hiking', 'Movies'],
    gender: 'male',
    lookingFor: ['female'],
    verified: false,
  },
  {
    id: 'user-4',
    name: 'Luna',
    age: 25,
    bio: 'Bookworm & plant mom. My voice is softer than my opinions.',
    photoUrl: 'https://images.unsplash.com/photo-1529626455594-4ff0802cfb7e?w=400',
    voiceIntroUrl: 'voice-4.m4a',
    voiceIntroDuration: 20,
    location: 'Williamsburg, NY',
    interests: ['Reading', 'Plants', 'Tea', 'Writing'],
    gender: 'female',
    lookingFor: ['male', 'female', 'non-binary'],
    verified: true,
  },
  {
    id: 'user-5',
    name: 'Alex',
    age: 28,
    bio: 'Architect who loves building connections as much as buildings',
    photoUrl: 'https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=400',
    voiceIntroUrl: 'voice-5.m4a',
    voiceIntroDuration: 16,
    location: 'SoHo, NY',
    interests: ['Architecture', 'Design', 'Running', 'Wine'],
    gender: 'male',
    lookingFor: ['female'],
    verified: true,
  },
];

const now = new Date();
const minutesAgo = (mins: number) => new Date(now.getTime() - mins * 60000);
const hoursAgo = (hrs: number) => new Date(now.getTime() - hrs * 3600000);

export const mockMessages: Record<string, VoiceMessage[]> = {
  'match-1': [
    { id: 'msg-1', senderId: 'user-1', receiverId: 'current-user', audioUrl: '', duration: 8, timestamp: hoursAgo(5), isPlayed: true, waveform: generateWaveform() },
    { id: 'msg-2', senderId: 'current-user', receiverId: 'user-1', audioUrl: '', duration: 12, timestamp: hoursAgo(4.5), isPlayed: true, waveform: generateWaveform() },
    { id: 'msg-3', senderId: 'user-1', receiverId: 'current-user', audioUrl: '', duration: 15, timestamp: hoursAgo(4), isPlayed: true, waveform: generateWaveform() },
    { id: 'msg-4', senderId: 'current-user', receiverId: 'user-1', audioUrl: '', duration: 10, timestamp: hoursAgo(3.5), isPlayed: true, waveform: generateWaveform() },
    { id: 'msg-5', senderId: 'user-1', receiverId: 'current-user', audioUrl: '', duration: 20, timestamp: hoursAgo(3), isPlayed: true, waveform: generateWaveform() },
    { id: 'msg-6', senderId: 'current-user', receiverId: 'user-1', audioUrl: '', duration: 7, timestamp: hoursAgo(2.5), isPlayed: true, waveform: generateWaveform() },
    { id: 'msg-7', senderId: 'user-1', receiverId: 'current-user', audioUrl: '', duration: 11, timestamp: hoursAgo(2), isPlayed: true, waveform: generateWaveform() },
    { id: 'msg-8', senderId: 'current-user', receiverId: 'user-1', audioUrl: '', duration: 9, timestamp: hoursAgo(1.5), isPlayed: true, waveform: generateWaveform() },
    { id: 'msg-9', senderId: 'user-1', receiverId: 'current-user', audioUrl: '', duration: 14, timestamp: hoursAgo(1), isPlayed: true, waveform: generateWaveform() },
    { id: 'msg-10', senderId: 'current-user', receiverId: 'user-1', audioUrl: '', duration: 6, timestamp: minutesAgo(30), isPlayed: true, waveform: generateWaveform() },
    { id: 'msg-11', senderId: 'user-1', receiverId: 'current-user', audioUrl: '', duration: 18, timestamp: minutesAgo(10), isPlayed: false, waveform: generateWaveform() },
  ],
  'match-2': [
    { id: 'msg-20', senderId: 'user-4', receiverId: 'current-user', audioUrl: '', duration: 10, timestamp: hoursAgo(2), isPlayed: true, waveform: generateWaveform() },
    { id: 'msg-21', senderId: 'current-user', receiverId: 'user-4', audioUrl: '', duration: 8, timestamp: hoursAgo(1.5), isPlayed: true, waveform: generateWaveform() },
    { id: 'msg-22', senderId: 'user-4', receiverId: 'current-user', audioUrl: '', duration: 13, timestamp: minutesAgo(45), isPlayed: false, waveform: generateWaveform() },
  ],
  'match-3': [
    { id: 'msg-30', senderId: 'user-5', receiverId: 'current-user', audioUrl: '', duration: 5, timestamp: hoursAgo(8), isPlayed: true, waveform: generateWaveform() },
  ],
};

export const mockMatches: Match[] = [
  {
    id: 'match-1',
    users: ['current-user', 'user-1'],
    createdAt: hoursAgo(48),
    lastMessage: mockMessages['match-1'][mockMessages['match-1'].length - 1],
    messageCount: 11,
    photosRevealed: true,
    unreadCount: 1,
  },
  {
    id: 'match-2',
    users: ['current-user', 'user-4'],
    createdAt: hoursAgo(24),
    lastMessage: mockMessages['match-2'][mockMessages['match-2'].length - 1],
    messageCount: 3,
    photosRevealed: false,
    unreadCount: 1,
  },
  {
    id: 'match-3',
    users: ['current-user', 'user-5'],
    createdAt: hoursAgo(12),
    lastMessage: mockMessages['match-3'][0],
    messageCount: 1,
    photosRevealed: false,
    unreadCount: 0,
  },
];

export const getMatchUser = (match: Match, currentUserId: string): User | undefined => {
  const otherId = match.users.find(id => id !== currentUserId);
  return [...discoverProfiles, currentUser].find(u => u.id === otherId);
};

export const PHOTO_REVEAL_THRESHOLD = 10;
