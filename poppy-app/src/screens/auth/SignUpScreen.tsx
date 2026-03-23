import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TextInput,
  ScrollView,
  TouchableOpacity,
  StatusBar,
  KeyboardAvoidingView,
  Platform,
} from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { Ionicons } from '@expo/vector-icons';
import { Colors, Typography, Spacing, BorderRadius, Shadows } from '../../theme';
import { PoppyButton } from '../../components/PoppyButton';
import { VoiceRecordButton } from '../../components/VoiceRecordButton';
import { useApp } from '../../context/AppContext';

interface SignUpScreenProps {
  navigation: any;
}

export const SignUpScreen: React.FC<SignUpScreenProps> = ({ navigation }) => {
  const { login } = useApp();
  const [step, setStep] = useState(1);
  const [name, setName] = useState('');
  const [age, setAge] = useState('');
  const [bio, setBio] = useState('');
  const [gender, setGender] = useState('');
  const [hasVoiceIntro, setHasVoiceIntro] = useState(false);

  const totalSteps = 4;

  const genderOptions = [
    { label: 'Woman', value: 'female', icon: 'flower-outline' },
    { label: 'Man', value: 'male', icon: 'person-outline' },
    { label: 'Non-binary', value: 'non-binary', icon: 'sparkles-outline' },
    { label: 'Other', value: 'other', icon: 'heart-outline' },
  ];

  const handleComplete = () => {
    login();
  };

  const renderStep = () => {
    switch (step) {
      case 1:
        return (
          <View style={styles.stepContent}>
            <Text style={styles.stepTitle}>What's your name?</Text>
            <Text style={styles.stepSubtitle}>
              This is how you'll appear on Poppy
            </Text>
            <TextInput
              style={styles.input}
              value={name}
              onChangeText={setName}
              placeholder="Your first name"
              placeholderTextColor={Colors.gray}
              autoFocus
            />
            <TextInput
              style={styles.input}
              value={age}
              onChangeText={setAge}
              placeholder="Your age"
              placeholderTextColor={Colors.gray}
              keyboardType="number-pad"
            />
          </View>
        );

      case 2:
        return (
          <View style={styles.stepContent}>
            <Text style={styles.stepTitle}>I identify as...</Text>
            <Text style={styles.stepSubtitle}>
              Select what best describes you
            </Text>
            <View style={styles.genderGrid}>
              {genderOptions.map(option => (
                <TouchableOpacity
                  key={option.value}
                  style={[
                    styles.genderOption,
                    gender === option.value && styles.genderOptionSelected,
                  ]}
                  onPress={() => setGender(option.value)}
                  activeOpacity={0.7}
                >
                  <Ionicons
                    name={option.icon as any}
                    size={24}
                    color={
                      gender === option.value ? Colors.primary : Colors.gray
                    }
                  />
                  <Text
                    style={[
                      styles.genderLabel,
                      gender === option.value && styles.genderLabelSelected,
                    ]}
                  >
                    {option.label}
                  </Text>
                </TouchableOpacity>
              ))}
            </View>
          </View>
        );

      case 3:
        return (
          <View style={styles.stepContent}>
            <Text style={styles.stepTitle}>Tell us about you</Text>
            <Text style={styles.stepSubtitle}>
              A short bio that captures your essence
            </Text>
            <TextInput
              style={[styles.input, styles.bioInput]}
              value={bio}
              onChangeText={setBio}
              placeholder="I love long walks, great conversations, and..."
              placeholderTextColor={Colors.gray}
              multiline
              numberOfLines={4}
              textAlignVertical="top"
            />
          </View>
        );

      case 4:
        return (
          <View style={styles.stepContent}>
            <Text style={styles.stepTitle}>Record your voice intro</Text>
            <Text style={styles.stepSubtitle}>
              This is what others will hear first. Make it count!
              {'\n'}Tell people what makes you, you.
            </Text>

            <View style={styles.voiceRecordArea}>
              <VoiceRecordButton
                onRecordComplete={(duration) => setHasVoiceIntro(true)}
                size={88}
              />

              {hasVoiceIntro && (
                <View style={styles.recordedBadge}>
                  <Ionicons
                    name="checkmark-circle"
                    size={20}
                    color={Colors.success}
                  />
                  <Text style={styles.recordedText}>
                    Voice intro recorded!
                  </Text>
                </View>
              )}
            </View>

            <View style={styles.tips}>
              <Text style={styles.tipTitle}>Tips for a great intro:</Text>
              {[
                'Be yourself - authenticity is attractive',
                'Share what you\'re passionate about',
                'Keep it between 10-30 seconds',
                'Smile while recording - it shows in your voice!',
              ].map((tip, i) => (
                <View key={i} style={styles.tipRow}>
                  <View style={styles.tipDot} />
                  <Text style={styles.tipText}>{tip}</Text>
                </View>
              ))}
            </View>
          </View>
        );

      default:
        return null;
    }
  };

  return (
    <KeyboardAvoidingView
      style={{ flex: 1 }}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
    >
      <LinearGradient
        colors={['#FFF0F8', '#FFFFFF'] as [string, string]}
        style={styles.container}
      >
        <StatusBar barStyle="dark-content" />

        {/* Header */}
        <View style={styles.header}>
          <TouchableOpacity
            onPress={() => (step > 1 ? setStep(step - 1) : navigation.goBack())}
            style={styles.backBtn}
          >
            <Ionicons name="chevron-back" size={24} color={Colors.primary} />
          </TouchableOpacity>

          {/* Progress bar */}
          <View style={styles.progressBar}>
            {Array.from({ length: totalSteps }).map((_, i) => (
              <View
                key={i}
                style={[
                  styles.progressDot,
                  {
                    backgroundColor:
                      i < step ? Colors.primary : Colors.lightGray,
                    flex: i < step ? 1.2 : 1,
                  },
                ]}
              />
            ))}
          </View>

          <Text style={styles.stepIndicator}>
            {step}/{totalSteps}
          </Text>
        </View>

        <ScrollView
          style={styles.scroll}
          contentContainerStyle={styles.scrollContent}
          keyboardShouldPersistTaps="handled"
          showsVerticalScrollIndicator={false}
        >
          {renderStep()}
        </ScrollView>

        {/* Bottom action */}
        <View style={styles.bottomAction}>
          <PoppyButton
            title={step === totalSteps ? "Let's bloom!" : 'Continue'}
            onPress={() => {
              if (step < totalSteps) {
                setStep(step + 1);
              } else {
                handleComplete();
              }
            }}
            size="large"
            disabled={
              (step === 1 && (!name || !age)) ||
              (step === 2 && !gender)
            }
          />
        </View>
      </LinearGradient>
    </KeyboardAvoidingView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: Spacing.md,
    paddingTop: Spacing.xxl + 10,
    gap: Spacing.md,
  },
  backBtn: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: Colors.primarySoft,
    alignItems: 'center',
    justifyContent: 'center',
  },
  progressBar: {
    flex: 1,
    flexDirection: 'row',
    gap: 4,
    height: 4,
  },
  progressDot: {
    height: 4,
    borderRadius: 2,
  },
  stepIndicator: {
    ...Typography.labelSmall,
    color: Colors.gray,
  },
  scroll: {
    flex: 1,
  },
  scrollContent: {
    padding: Spacing.xl,
    paddingBottom: 120,
  },
  stepContent: {
    marginTop: Spacing.xl,
  },
  stepTitle: {
    ...Typography.displaySmall,
    color: Colors.black,
    marginBottom: Spacing.sm,
  },
  stepSubtitle: {
    ...Typography.bodyMedium,
    color: Colors.gray,
    marginBottom: Spacing.xl,
  },
  input: {
    backgroundColor: Colors.white,
    borderRadius: BorderRadius.lg,
    padding: Spacing.md,
    ...Typography.bodyLarge,
    color: Colors.black,
    borderWidth: 2,
    borderColor: Colors.lightGray,
    marginBottom: Spacing.md,
    ...Shadows.soft,
  },
  bioInput: {
    minHeight: 120,
  },
  genderGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Spacing.md,
  },
  genderOption: {
    width: '47%',
    padding: Spacing.lg,
    backgroundColor: Colors.white,
    borderRadius: BorderRadius.lg,
    alignItems: 'center',
    gap: Spacing.sm,
    borderWidth: 2,
    borderColor: Colors.lightGray,
    ...Shadows.soft,
  },
  genderOptionSelected: {
    borderColor: Colors.primary,
    backgroundColor: Colors.primarySoft,
  },
  genderLabel: {
    ...Typography.labelMedium,
    color: Colors.darkGray,
  },
  genderLabelSelected: {
    color: Colors.primary,
  },
  voiceRecordArea: {
    alignItems: 'center',
    paddingVertical: Spacing.xl,
    gap: Spacing.lg,
  },
  recordedBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.xs,
    backgroundColor: '#E8F5E9',
    paddingHorizontal: Spacing.md,
    paddingVertical: Spacing.sm,
    borderRadius: BorderRadius.round,
  },
  recordedText: {
    ...Typography.labelMedium,
    color: Colors.success,
  },
  tips: {
    backgroundColor: Colors.primarySoft,
    borderRadius: BorderRadius.lg,
    padding: Spacing.lg,
  },
  tipTitle: {
    ...Typography.labelMedium,
    color: Colors.primary,
    marginBottom: Spacing.sm,
  },
  tipRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: Spacing.sm,
    marginBottom: Spacing.xs,
  },
  tipDot: {
    width: 6,
    height: 6,
    borderRadius: 3,
    backgroundColor: Colors.primary,
    marginTop: 6,
  },
  tipText: {
    ...Typography.bodySmall,
    color: Colors.darkGray,
    flex: 1,
  },
  bottomAction: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    padding: Spacing.xl,
    paddingBottom: Spacing.xxl,
    backgroundColor: 'rgba(255,255,255,0.95)',
  },
});
