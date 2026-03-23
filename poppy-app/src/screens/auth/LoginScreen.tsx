import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TextInput,
  TouchableOpacity,
  StatusBar,
  KeyboardAvoidingView,
  Platform,
} from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { Ionicons } from '@expo/vector-icons';
import { Colors, Typography, Spacing, BorderRadius, Shadows } from '../../theme';
import { PoppyButton } from '../../components/PoppyButton';
import { useApp } from '../../context/AppContext';

interface LoginScreenProps {
  navigation: any;
}

export const LoginScreen: React.FC<LoginScreenProps> = ({ navigation }) => {
  const { login } = useApp();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);

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

        <TouchableOpacity
          onPress={() => navigation.goBack()}
          style={styles.backBtn}
        >
          <Ionicons name="chevron-back" size={24} color={Colors.primary} />
        </TouchableOpacity>

        <View style={styles.content}>
          {/* Logo */}
          <View style={styles.logoArea}>
            <LinearGradient
              colors={Colors.gradientPrimary as unknown as [string, string]}
              style={styles.logo}
            >
              <Ionicons name="mic" size={36} color={Colors.white} />
            </LinearGradient>
            <Text style={styles.title}>Welcome back</Text>
            <Text style={styles.subtitle}>
              Your voice has been missed
            </Text>
          </View>

          {/* Form */}
          <View style={styles.form}>
            <View style={styles.inputContainer}>
              <Ionicons name="mail-outline" size={20} color={Colors.gray} />
              <TextInput
                style={styles.input}
                value={email}
                onChangeText={setEmail}
                placeholder="Email address"
                placeholderTextColor={Colors.gray}
                keyboardType="email-address"
                autoCapitalize="none"
              />
            </View>

            <View style={styles.inputContainer}>
              <Ionicons
                name="lock-closed-outline"
                size={20}
                color={Colors.gray}
              />
              <TextInput
                style={styles.input}
                value={password}
                onChangeText={setPassword}
                placeholder="Password"
                placeholderTextColor={Colors.gray}
                secureTextEntry={!showPassword}
              />
              <TouchableOpacity
                onPress={() => setShowPassword(!showPassword)}
              >
                <Ionicons
                  name={showPassword ? 'eye-off-outline' : 'eye-outline'}
                  size={20}
                  color={Colors.gray}
                />
              </TouchableOpacity>
            </View>

            <TouchableOpacity style={styles.forgotBtn}>
              <Text style={styles.forgotText}>Forgot password?</Text>
            </TouchableOpacity>
          </View>

          <PoppyButton
            title="Sign In"
            onPress={login}
            size="large"
            disabled={!email || !password}
          />

          {/* Social login */}
          <View style={styles.divider}>
            <View style={styles.dividerLine} />
            <Text style={styles.dividerText}>or continue with</Text>
            <View style={styles.dividerLine} />
          </View>

          <View style={styles.socialRow}>
            {['logo-apple', 'logo-google', 'call-outline'].map((icon, i) => (
              <TouchableOpacity
                key={i}
                style={styles.socialBtn}
                onPress={login}
                activeOpacity={0.7}
              >
                <Ionicons
                  name={icon as any}
                  size={24}
                  color={Colors.darkGray}
                />
              </TouchableOpacity>
            ))}
          </View>
        </View>
      </LinearGradient>
    </KeyboardAvoidingView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  backBtn: {
    marginTop: Spacing.xxl + 10,
    marginLeft: Spacing.md,
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: Colors.primarySoft,
    alignItems: 'center',
    justifyContent: 'center',
  },
  content: {
    flex: 1,
    paddingHorizontal: Spacing.xl,
    justifyContent: 'center',
  },
  logoArea: {
    alignItems: 'center',
    marginBottom: Spacing.xxl,
  },
  logo: {
    width: 72,
    height: 72,
    borderRadius: 36,
    alignItems: 'center',
    justifyContent: 'center',
    ...Shadows.glow,
    marginBottom: Spacing.md,
  },
  title: {
    ...Typography.displaySmall,
    color: Colors.black,
  },
  subtitle: {
    ...Typography.bodyMedium,
    color: Colors.gray,
    marginTop: Spacing.xs,
  },
  form: {
    gap: Spacing.md,
    marginBottom: Spacing.xl,
  },
  inputContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: Colors.white,
    borderRadius: BorderRadius.lg,
    paddingHorizontal: Spacing.md,
    gap: Spacing.sm,
    borderWidth: 2,
    borderColor: Colors.lightGray,
    ...Shadows.soft,
  },
  input: {
    flex: 1,
    paddingVertical: Spacing.md,
    ...Typography.bodyLarge,
    color: Colors.black,
  },
  forgotBtn: {
    alignSelf: 'flex-end',
  },
  forgotText: {
    ...Typography.labelSmall,
    color: Colors.primary,
  },
  divider: {
    flexDirection: 'row',
    alignItems: 'center',
    marginVertical: Spacing.xl,
    gap: Spacing.md,
  },
  dividerLine: {
    flex: 1,
    height: 1,
    backgroundColor: Colors.lightGray,
  },
  dividerText: {
    ...Typography.caption,
    color: Colors.gray,
  },
  socialRow: {
    flexDirection: 'row',
    justifyContent: 'center',
    gap: Spacing.lg,
  },
  socialBtn: {
    width: 56,
    height: 56,
    borderRadius: 28,
    backgroundColor: Colors.white,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 2,
    borderColor: Colors.lightGray,
    ...Shadows.soft,
  },
});
