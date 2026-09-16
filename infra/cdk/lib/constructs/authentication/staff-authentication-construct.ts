import {
  Duration,
  RemovalPolicy,
  aws_certificatemanager as acm,
  aws_cognito as cognito,
} from "aws-cdk-lib";
import { Construct } from "constructs";

interface StaffAuthenticationConstructProps {
  edgeCertificate: acm.ICertificate;
  removalPolicy: RemovalPolicy;
  resourceNamePrefix: string;
  staffAuthDomainName: string;
  staffOAuthCallbackUrls: string[];
  staffOAuthLogoutUrls: string[];
  staffUserPoolDomainPrefix: string;
  userPoolDeletionProtection: boolean;
}

export class StaffAuthenticationConstruct extends Construct {
  public readonly appClient: cognito.IUserPoolClient;
  public readonly customDomain: cognito.UserPoolDomain;
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

    const userPoolDomain = this.userPool.addDomain("StaffUserPoolDomain", {
      cognitoDomain: {
        domainPrefix: props.staffUserPoolDomainPrefix,
      },
      managedLoginVersion: cognito.ManagedLoginVersion.NEWER_MANAGED_LOGIN,
    });

    this.customDomain = this.userPool.addDomain("StaffCustomDomain", {
      customDomain: {
        certificate: props.edgeCertificate,
        domainName: props.staffAuthDomainName,
      },
      managedLoginVersion: cognito.ManagedLoginVersion.NEWER_MANAGED_LOGIN,
    });

    this.appClient = new cognito.UserPoolClient(this, "StaffAppClient", {
      accessTokenValidity: Duration.minutes(60),
      enableTokenRevocation: true,
      generateSecret: false,
      idTokenValidity: Duration.minutes(60),
      oAuth: {
        callbackUrls: props.staffOAuthCallbackUrls,
        flows: {
          authorizationCodeGrant: true,
          implicitCodeGrant: false,
        },
        logoutUrls: props.staffOAuthLogoutUrls,
        scopes: [cognito.OAuthScope.OPENID, cognito.OAuthScope.EMAIL],
      },
      preventUserExistenceErrors: true,
      refreshTokenRotationGracePeriod: Duration.seconds(10),
      refreshTokenValidity: Duration.hours(8),
      userPool: this.userPool,
      userPoolClientName: `${props.resourceNamePrefix}-staff-app-client`,
    });

    const managedLoginBranding = new cognito.CfnManagedLoginBranding(
      this,
      "StaffManagedLoginBranding",
      {
        clientId: this.appClient.userPoolClientId,
        useCognitoProvidedValues: true,
        userPoolId: this.userPool.userPoolId,
      },
    );

    managedLoginBranding.node.addDependency(userPoolDomain);
  }
}
