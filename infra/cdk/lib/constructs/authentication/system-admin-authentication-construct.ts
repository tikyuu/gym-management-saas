import {
  Duration,
  RemovalPolicy,
  aws_cognito as cognito,
} from "aws-cdk-lib";
import { Construct } from "constructs";

interface SystemAdminAuthenticationConstructProps {
  removalPolicy: RemovalPolicy;
  resourceNamePrefix: string;
  userPoolDeletionProtection: boolean;
}

export class SystemAdminAuthenticationConstruct extends Construct {
  public readonly userPool: cognito.IUserPool;

  constructor(
    scope: Construct,
    id: string,
    props: SystemAdminAuthenticationConstructProps,
  ) {
    super(scope, id);

    this.userPool = new cognito.UserPool(this, "SystemAdminUserPool", {
      accountRecovery: cognito.AccountRecovery.EMAIL_ONLY,
      deletionProtection: props.userPoolDeletionProtection,
      featurePlan: cognito.FeaturePlan.ESSENTIALS,
      mfa: cognito.Mfa.REQUIRED,
      mfaSecondFactor: {
        otp: true,
        sms: false,
      },
      passwordPolicy: {
        minLength: 8,
        requireDigits: true,
        requireLowercase: true,
        requireSymbols: true,
        requireUppercase: true,
        tempPasswordValidity: Duration.days(7),
      },
      removalPolicy: props.removalPolicy,
      selfSignUpEnabled: false,
      signInAliases: {
        email: true,
      },
      signInCaseSensitive: false,
      userPoolName: `${props.resourceNamePrefix}-system-admin-user-pool`,
    });
  }
}
