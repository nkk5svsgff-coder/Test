import React, { useState, useRef } from 'react';
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { LinearGradient } from 'expo-linear-gradient';
import { Colors, Typography, Spacing, BorderRadius, Shadows } from '../theme';
import { VoiceWaveform } from './VoiceWaveform';
import { VoiceMessage } from '../types';

interface VoiceMessageBubbleProps {
  message: VoiceMessage;
  isMine: boolean;
}

export const VoiceMessageBubble: React.FC<VoiceMessageBubbleProps> = ({
  message,
  isMine,
}) => {
  const [isPlaying, setIsPlaying] = useState(false);
  const [progress, setProgress] = useState(0);
  const progressRef = useRef<ReturnType<typeof setInterval>>(undefined);

  const togglePlay = () => {
    if (isPlaying) {
      setIsPlaying(false);
      if (progressRef.current) clearInterval(progressRef.current);
    } else {
      setIsPlaying(true);
      setProgress(0);
      progressRef.current = setInterval(() => {
        setProgress(prev => {
          if (prev >= 100) {
            setIsPlaying(false);
            if (progressRef.current) clearInterval(progressRef.current);
            return 0;
          }
          return prev + (100 / (message.duration * 10));
        });
      }, 100);
    }
  };

  const formatTime = (seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const formatTimestamp = (date: Date): string => {
    const d = new Date(date);
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  const bubbleContent = (
    <View style={[styles.bubble, isMine ? styles.mineBubble : styles.theirBubble]}>
      <TouchableOpacity
        onPress={togglePlay}
        style={[
          styles.playBtn,
          { backgroundColor: isMine ? 'rgba(255,255,255,0.3)' : Colors.primarySoft },
        ]}
        activeOpacity={0.7}
      >
        <Ionicons
          name={isPlaying ? 'pause' : 'play'}
          size={18}
          color={isMine ? Colors.white : Colors.primary}
        />
      </TouchableOpacity>

      <View style={styles.waveformArea}>
        <VoiceWaveform
          waveform={message.waveform}
          isPlaying={isPlaying}
          color={isMine ? Colors.white : Colors.primary}
          height={28}
          barCount={18}
        />
        <View style={[styles.progressTrack, { backgroundColor: isMine ? 'rgba(255,255,255,0.2)' : Colors.lightGray }]}>
          <View
            style={[
              styles.progressFill,
              {
                width: `${progress}%`,
                backgroundColor: isMine ? Colors.white : Colors.primary,
              },
            ]}
          />
        </View>
      </View>

      <View style={styles.meta}>
        <Text style={[styles.duration, { color: isMine ? 'rgba(255,255,255,0.8)' : Colors.gray }]}>
          {formatTime(message.duration)}
        </Text>
      </View>
    </View>
  );

  return (
    <View style={[styles.container, isMine ? styles.mineContainer : styles.theirContainer]}>
      {isMine ? (
        <LinearGradient
          colors={Colors.gradientPrimary as unknown as [string, string]}
          start={{ x: 0, y: 0 }}
          end={{ x: 1, y: 0 }}
          style={[styles.gradientWrap, Shadows.soft]}
        >
          {bubbleContent}
        </LinearGradient>
      ) : (
        <View style={[styles.theirWrap, Shadows.soft]}>
          {bubbleContent}
        </View>
      )}
      <Text style={styles.timestamp}>{formatTimestamp(message.timestamp)}</Text>
      {isMine && !message.isPlayed && (
        <View style={styles.unread}>
          <Ionicons name="checkmark" size={12} color={Colors.gray} />
        </View>
      )}
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    marginVertical: Spacing.xs,
    maxWidth: '80%',
  },
  mineContainer: {
    alignSelf: 'flex-end',
    marginRight: Spacing.md,
  },
  theirContainer: {
    alignSelf: 'flex-start',
    marginLeft: Spacing.md,
  },
  gradientWrap: {
    borderRadius: BorderRadius.lg,
    borderBottomRightRadius: 4,
  },
  theirWrap: {
    borderRadius: BorderRadius.lg,
    borderBottomLeftRadius: 4,
    backgroundColor: Colors.white,
  },
  bubble: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: Spacing.sm,
    gap: Spacing.sm,
  },
  mineBubble: {},
  theirBubble: {},
  playBtn: {
    width: 36,
    height: 36,
    borderRadius: 18,
    alignItems: 'center',
    justifyContent: 'center',
  },
  waveformArea: {
    flex: 1,
  },
  progressTrack: {
    height: 2,
    borderRadius: 1,
    marginTop: 4,
    overflow: 'hidden',
  },
  progressFill: {
    height: '100%',
    borderRadius: 1,
  },
  meta: {
    alignItems: 'flex-end',
  },
  duration: {
    ...Typography.labelSmall,
  },
  timestamp: {
    ...Typography.caption,
    color: Colors.gray,
    marginTop: 2,
    alignSelf: 'flex-end',
    marginHorizontal: 4,
  },
  unread: {
    position: 'absolute',
    bottom: 2,
    right: -2,
  },
});
