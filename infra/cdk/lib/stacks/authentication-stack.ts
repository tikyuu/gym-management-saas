import {
  RemovalPolicy,
  Stack,
  StackProps,
  Tags,
  aws_certificatemanager as acm,
  aws_cognito as cognito,
} from "aws-cdk-lib";
import { Construct } from "constructs";
import { CustomerAuthenticationConstruct } from "../constructs/authentication/customer-authentication-construct";
import { StaffAuthenticationConstruct } from "../constructs/authentication/staff-authentication-construct";
import { SystemAdminAuthenticationConstruct } from "../constructs/authentication/system-admin-authentication-construct";

interface AuthenticationStackProps extends StackProps {
  applicationName: string;
  customerOAuthCallbackUrls: string[];
  customerOAuthLogoutUrls: string[];
  customerUserPoolDomainPrefix: string;
  edgeCertificate: acm.ICertificate;
  environmentName: string;
  removalPolicy: RemovalPolicy;
  staffOAuthCallbackUrls: string[];
  staffOAuthLogoutUrls: string[];
  staffUserPoolDomainPrefix: string;
  systemAdminOAuthCallbackUrls: string[];
  systemAdminOAuthLogoutUrls: string[];
  systemAdminUserPoolDomainPrefix: string;
  userPoolDeletionProtection: boolean;
}

export class AuthenticationStack extends Stack {
  public readonly customerAppClient: cognito.IUserPoolClient;
  public readonly customerUserPool: cognito.IUserPool;
  public readonly staffAppClient: cognito.IUserPoolClient;
  public readonly staffUserPool: cognito.IUserPool;
  public readonly systemAdminAppClient: cognito.IUserPoolClient;
  public readonly systemAdminUserPool: cognito.IUserPool;

  constructor(scope: Construct, id: string, props: AuthenticationStackProps) {
    super(scope, id, props);

    const resourceNamePrefix = `${props.applicationName}-${props.environmentName}`;

    Tags.of(this).add("application", props.applicationName);
    Tags.of(this).add("environment", props.environmentName);
    Tags.of(this).add("managed-by", "aws-cdk");
    Tags.of(this).add("component", "authentication");

    const customerAuthentication = new CustomerAuthenticationConstruct(
      this,
      "CustomerAuthentication",
      {
        customerOAuthCallbackUrls: props.customerOAuthCallbackUrls,
        customerOAuthLogoutUrls: props.customerOAuthLogoutUrls,
        customerUserPoolDomainPrefix: props.customerUserPoolDomainPrefix,
        removalPolicy: props.removalPolicy,
        resourceNamePrefix,
        userPoolDeletionProtection: props.userPoolDeletionProtection,
      },
    );

    this.customerAppClient = customerAuthentication.appClient;
    this.customerUserPool = customerAuthentication.userPool;

    const staffAuthentication = new StaffAuthenticationConstruct(
      this,
      "StaffAuthentication",
      {
        removalPolicy: props.removalPolicy,
        resourceNamePrefix,
        staffOAuthCallbackUrls: props.staffOAuthCallbackUrls,
        staffOAuthLogoutUrls: props.staffOAuthLogoutUrls,
        staffUserPoolDomainPrefix: props.staffUserPoolDomainPrefix,
        userPoolDeletionProtection: props.userPoolDeletionProtection,
      },
    );

    this.staffAppClient = staffAuthentication.appClient;
    this.staffUserPool = staffAuthentication.userPool;

    const systemAdminAuthentication = new SystemAdminAuthenticationConstruct(
      this,
      "SystemAdminAuthentication",
      {
        removalPolicy: props.removalPolicy,
        resourceNamePrefix,
        systemAdminOAuthCallbackUrls: props.systemAdminOAuthCallbackUrls,
        systemAdminOAuthLogoutUrls: props.systemAdminOAuthLogoutUrls,
        systemAdminUserPoolDomainPrefix:
          props.systemAdminUserPoolDomainPrefix,
        userPoolDeletionProtection: props.userPoolDeletionProtection,
      },
    );

    this.systemAdminAppClient = systemAdminAuthentication.appClient;
    this.systemAdminUserPool = systemAdminAuthentication.userPool;
  }
}
