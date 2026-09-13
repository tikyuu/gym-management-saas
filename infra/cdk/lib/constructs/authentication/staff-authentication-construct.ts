import {
  Duration,
  RemovalPolicy,
  aws_cognito as cognito,
} from "aws-cdk-lib";
import { Construct } from "constructs";

interface StaffAuthenticationConstructProps {
  removalPolicy: RemovalPolicy;
  resourceNamePrefix: string;
  userPoolDeletionProtection: boolean;
}

export class StaffAuthenticationConstruct extends Construct {
  public readonly appClient: cognito.IUserPoolClient;
  public readonly userPool: cognito.IUserPool;

  constructor(
    scope: Construct,
    id: string,
    props: StaffAuthenticationConstructProps,
  ) {
    super(scope, id);

    this.userPool = new cognito.UserPool(this, "StaffUserPool", {
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
      userPoolName: `${props.resourceNamePrefix}-staff-user-pool`,
    });

    this.appClient = new cognito.UserPoolClient(this, "StaffAppClient", {
      accessTokenValidity: Duration.minutes(60),
      disableOAuth: true,
      enableTokenRevocation: true,
      generateSecret: false,
      idTokenValidity: Duration.minutes(60),
      preventUserExistenceErrors: true,
      refreshTokenRotationGracePeriod: Duration.seconds(10),
      refreshTokenValidity: Duration.hours(8),
      userPool: this.userPool,
      userPoolClientName: `${props.resourceNamePrefix}-staff-app-client`,
    });
  }
}
